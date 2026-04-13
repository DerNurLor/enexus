'use client'
/**
 * web/app/map/page.tsx
 *
 * Google Maps-стиль: карта 100% viewport, всё поверх неё как floating UI.
 * Левая панель — абсолютная, поверх карты, с blur-фоном.
 * Карта НЕ зависит от размера панелей.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  MapPin, Search, X, Navigation, Building2, BedDouble,
  Utensils, CreditCard, Info, Loader2, ExternalLink, Bus,
  ChevronRight, DoorOpen, List, Map as MapIcon,
} from 'lucide-react'
import { useScheduleStore } from '@/lib/store'
import { useRouter } from 'next/navigation'

// ── Типы ──────────────────────────────────────────────────────────────────────

interface CampusItem {
  id: string; source_id: string; city_id: string; city_title: string
  title: string; full_title: string; address: string; photo: string
  lat: number | null; lon: number | null
  transport: { bus: string; trolleybus: string; tram: string }
  type: { id: string; title: string }
}

interface CityInfo {
  id: string; title: string; total: number; by_type: Record<string, number>
}

// ── Константы ─────────────────────────────────────────────────────────────────

const TYPE_META: Record<string, { label: string; markerColor: string; icon: any }> = {
  campuses: { label: 'Корпуса',       markerColor: '#6366f1', icon: Building2 },
  hostels:  { label: 'Общежития',     markerColor: '#10b981', icon: BedDouble  },
  cafe:     { label: 'Буфеты',        markerColor: '#f97316', icon: Utensils   },
  banks:    { label: 'Банкоматы',     markerColor: '#f59e0b', icon: CreditCard },
  misc:     { label: 'Доп. объекты',  markerColor: '#64748b', icon: Info       },
}

// Координаты центров городов — СКФУ campus area
const CITY_CENTERS: Record<string, [number, number, number]> = {
  '838': [45.0430, 41.9618, 15],  // Ставрополь — ул. Пушкина (центр кампуса)
  '832': [44.0432, 43.0555, 15],  // Пятигорск
  '826': [44.6447, 41.9414, 16],  // Невинномысск
}

const API = (process.env.NEXT_PUBLIC_API_URL || '') + '/api'

// ── API helpers ───────────────────────────────────────────────────────────────

async function fetchCampuses(cityId?: string, typeId?: string, q?: string) {
  const p = new URLSearchParams({ with_coords: 'true', limit: '300' })
  if (cityId) p.set('city_id', cityId)
  if (typeId) p.set('type_id', typeId)
  if (q)     p.set('q', q)
  const res = await fetch(`${API}/campuses/?${p}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

async function fetchCities() {
  const res = await fetch(`${API}/campuses/cities`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

async function fetchFreeRooms(at: string) {
  const res = await fetch(`${API}/rooms/free?at=${encodeURIComponent(at)}&duration=90`)
  if (!res.ok) return null
  return res.json()
}

function isoNow() {
  const d = new Date()
  return `${d.toISOString().split('T')[0]}T${d.toTimeString().slice(0, 5)}`
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function MapPage() {
  const router = useRouter()
  const { setRoom, setMode, settings } = useScheduleStore()

  // Определяем тему — 'auto' читаем из класса <html>
  const getIsDark = () => {
    if (typeof window === 'undefined') return true
    const theme = settings?.theme ?? 'auto'
    if (theme === 'dark')  return true
    if (theme === 'light') return false
    // auto — смотрим на класс html который выставляет themeScript
    return document.documentElement.classList.contains('dark') ||
      (!document.documentElement.classList.contains('light') &&
       window.matchMedia('(prefers-color-scheme: dark)').matches)
  }


  // Leaflet refs
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const leafletRef      = useRef<any>(null)
  const mapObjRef       = useRef<any>(null)
  const markersRef      = useRef<Map<string, any>>(new Map())
  const clusterRef      = useRef<any>(null)
  const userMarkerRef   = useRef<any>(null)
  const selectedRef     = useRef<string | null>(null)
  const tileLayerRef    = useRef<any>(null)

  const TILES = {
    dark:  {
      url:         'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/">CARTO</a>',
    },
    light: {
      url:         'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  }


  // UI state
  const [selected,    setSelected]    = useState<CampusItem | null>(null)
  const [search,      setSearch]      = useState('')
  const [typeFilter,  setTypeFilter]  = useState<string>('all')
  const [cityFilter,  setCityFilter]  = useState<string>('838')
  const [mapReady,    setMapReady]    = useState(false)
  const [locating,    setLocating]    = useState(false)
  const [sideOpen,    setSideOpen]    = useState(true)   // desktop side panel
  const [mobileTab,   setMobileTab]   = useState<'map' | 'list'>('map')
  const [at,          setAt]          = useState(isoNow)

  useEffect(() => {
    const id = setInterval(() => setAt(isoNow()), 60_000)
    return () => clearInterval(id)
  }, [])

  // ── Data ──────────────────────────────────────────────────────────────────

  const { data: citiesData } = useQuery({
    queryKey: ['campus-cities'],
    queryFn: fetchCities,
    staleTime: 3600_000,
  })
  const cities: CityInfo[] = citiesData?.cities ?? []

  const { data: campusData, isLoading } = useQuery({
    queryKey: ['campuses', cityFilter, typeFilter, search],
    queryFn: () => fetchCampuses(
      cityFilter === 'all' ? undefined : cityFilter,
      typeFilter === 'all' ? undefined : typeFilter,
      search || undefined,
    ),
    staleTime: 300_000,
    placeholderData: (p) => p,
  })
  const items: CampusItem[] = campusData?.items ?? []

  const { data: freeRoomsData } = useQuery({
    queryKey: ['free-rooms-map', at.slice(0, 16)],
    queryFn: () => fetchFreeRooms(at),
    staleTime: 120_000,
    refetchInterval: 300_000,
  })
  const byBuilding: Record<string, any[]> = freeRoomsData?.by_building ?? {}

  function getFreeRooms(item: CampusItem): any[] | null {
    if (item.type.id !== 'campuses') return null
    const num = item.title.replace(/[^0-9А-Яа-яA-Za-z]/g, '')
    const key = Object.keys(byBuilding).find(k => k.includes(num) || k === num)
    return key ? byBuilding[key] : null
  }

  function openRoom(roomId: number, roomName: string) {
    setMode('room'); setRoom(roomId, roomName); router.push('/schedule')
  }

  // ── Leaflet init ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!mapContainerRef.current || mapObjRef.current) return

    const load = async () => {
      // CSS
      for (const [id, href] of [
        ['lf-css', 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css'],
        ['cl-css', 'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.min.css'],
      ] as [string, string][]) {
        if (!document.getElementById(id)) {
          const l = document.createElement('link'); l.id = id; l.rel = 'stylesheet'; l.href = href
          document.head.appendChild(l)
        }
      }
      // JS
      if (!(window as any).L) await new Promise<void>(r => {
        const s = document.createElement('script')
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'
        s.onload = () => r(); document.head.appendChild(s)
      })
      if (!(window as any).L?.markerClusterGroup) await new Promise<void>(r => {
        const s = document.createElement('script')
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.min.js'
        s.onload = () => r(); document.head.appendChild(s)
      })

      const L = (window as any).L
      leafletRef.current = L

      const [lat, lon, zoom] = CITY_CENTERS['838']
      const map = L.map(mapContainerRef.current!, {
        center: [lat, lon],
        zoom,
        zoomControl: false,
        attributionControl: true,
      })

      const isDark = getIsDark()
      const tiles  = isDark ? TILES.dark : TILES.light
      tileLayerRef.current = L.tileLayer(tiles.url, {
        attribution: tiles.attribution,
        maxZoom: 19,
      }).addTo(map)

      // Zoom в правый нижний угол
      L.control.zoom({ position: 'bottomright' }).addTo(map)

      mapObjRef.current = map
      setMapReady(true)
    }

    load()
    return () => {
      if (mapObjRef.current) { mapObjRef.current.remove(); mapObjRef.current = null }
    }
  }, [])

  // ── Маркеры ───────────────────────────────────────────────────────────────

  const makeIcon = useCallback((typeId: string, isSelected: boolean, label: string) => {
    const L = leafletRef.current; if (!L) return null
    const meta = TYPE_META[typeId] || TYPE_META.misc
    const size = isSelected ? 44 : 32
    const fs   = label.length > 4 ? 7 : label.length > 2 ? 9 : 11
    const bg   = isSelected ? meta.markerColor : '#fff'
    const fg   = isSelected ? '#fff' : meta.markerColor
    const sw   = isSelected ? 0 : 2.5
    // Пульсирующий ring только для selected — рисуем через HTML+CSS animation
    const pulse = isSelected ? `
      <div style="
        position:absolute;
        top:50%;left:50%;
        transform:translate(-50%,-60%);
        width:${size + 16}px;height:${size + 16}px;
        border-radius:50%;
        border:3px solid ${meta.markerColor};
        animation:pulse-ring 1.4s ease-out infinite;
        pointer-events:none;
      "></div>` : ''

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size + 8}" style="overflow:visible">
      <defs>
        <filter id="sh${isSelected ? 's' : 'n'}" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="${isSelected ? 4 : 2}" stdDeviation="${isSelected ? 4 : 2}" flood-opacity="${isSelected ? 0.45 : 0.3}"/>
        </filter>
      </defs>
      <circle cx="${size/2}" cy="${size/2}" r="${size/2 - 2}"
        fill="${bg}" stroke="${meta.markerColor}" stroke-width="${sw}"
        filter="url(#sh${isSelected ? 's' : 'n'})"/>
      <text x="${size/2}" y="${size/2 + 0.5}"
        text-anchor="middle" dominant-baseline="central"
        font-family="system-ui,-apple-system,sans-serif"
        font-size="${fs}" font-weight="700" fill="${fg}">${label}</text>
      <polygon
        points="${size/2 - 5},${size - 2} ${size/2 + 5},${size - 2} ${size/2},${size + 7}"
        fill="${meta.markerColor}"/>
    </svg>`

    return L.divIcon({
      html: `<div style="position:relative;display:flex;align-items:center;justify-content:center;">${pulse}${svg}</div>`,
      className: '',
      iconSize:   [size, size + 8],
      iconAnchor: [size / 2, size + 8],
      popupAnchor:[0, -(size + 8)],
    })
  }, [])

  useEffect(() => {
    const L = leafletRef.current; const map = mapObjRef.current
    if (!L || !map || !mapReady) return

    if (clusterRef.current) map.removeLayer(clusterRef.current)

    const cluster = L.markerClusterGroup({
      maxClusterRadius: 40,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: (c: any) => {
        const n = c.getChildCount()
        return L.divIcon({
          html: `<div style="
            width:36px;height:36px;border-radius:50%;
            background:#6366f1;color:#fff;
            display:flex;align-items:center;justify-content:center;
            font-size:13px;font-weight:700;
            border:2.5px solid #fff;
            box-shadow:0 2px 8px rgba(0,0,0,.35)
          ">${n}</div>`,
          className: '',
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        })
      },
    })
    clusterRef.current = cluster
    markersRef.current.clear()

    items.forEach(item => {
      if (item.lat === null || item.lon === null) return

      // Всегда создаём с isSelected=false — отдельный useEffect обновит иконку
      const icon = makeIcon(item.type.id, false, item.title)
      if (!icon) return

      const marker = L.marker([item.lat, item.lon], { icon })
      marker.on('click', () => {
        setSelected(item)
        // на мобиле переключаемся на карту
        setMobileTab('map')
      })
      marker.bindTooltip(
        `<div style="font-weight:600;font-size:12px">${item.full_title}</div>
         <div style="color:#888;font-size:11px;margin-top:2px">${item.address}</div>`,
        { direction: 'top', offset: [0, -52], className: 'campus-tooltip' }
      )
      markersRef.current.set(item.source_id, marker)
      cluster.addLayer(marker)
    })

    map.addLayer(cluster)

    // Сразу применяем выбранную иконку если есть selected
    if (selectedRef.current) {
      const m = markersRef.current.get(selectedRef.current)
      const selItem = items.find(i => i.source_id === selectedRef.current)
      if (m && selItem) {
        const selIcon = makeIcon(selItem.type.id, true, selItem.title)
        if (selIcon) m.setIcon(selIcon)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, mapReady])

  // Обновляем иконку при смене selected — только иконки, без пересоздания маркеров
  useEffect(() => {
    if (!mapReady) return
    selectedRef.current = selected?.source_id ?? null
    markersRef.current.forEach((marker, sid) => {
      const item = items.find(i => i.source_id === sid)
      if (!item) return
      const icon = makeIcon(item.type.id, selected?.source_id === sid, item.title)
      if (icon) marker.setIcon(icon)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, mapReady])

  // Меняем тайловый слой при смене темы
  useEffect(() => {
    const map = mapObjRef.current
    const L   = leafletRef.current
    if (!map || !L || !mapReady) return

    const isDark = getIsDark()
    const tiles  = isDark ? TILES.dark : TILES.light

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current)
    }
    tileLayerRef.current = L.tileLayer(tiles.url, {
      attribution: tiles.attribution,
      maxZoom: 19,
    }).addTo(map)
    // Опускаем tile layer под маркеры
    tileLayerRef.current.bringToBack()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings?.theme, mapReady])

  // При выборе объекта из списка — раскрываем кластер если маркер скрыт в нём
  const revealMarker = useCallback((sourceId: string) => {
    const cluster = clusterRef.current
    const marker  = markersRef.current.get(sourceId)
    if (!cluster || !marker) return
    // Проверяем видим ли маркер или скрыт в кластере
    const visible = cluster.getVisibleParent(marker)
    if (visible && visible !== marker) {
      // Маркер в кластере — зумируем до него чтобы раскрылся
      cluster.zoomToShowLayer(marker, () => {
        // После раскрытия открываем tooltip
        try { marker.openTooltip() } catch {}
      })
    }
  }, [])

  // Fly to selected — с гвардами от NaN
  const prevSelectedRef = useRef<string | null>(null)
  useEffect(() => {
    const map = mapObjRef.current
    if (!map || !mapReady || !selected) return
    // Не летим если тот же объект (предотвращаем повторный flyTo)
    if (prevSelectedRef.current === selected.source_id) return
    prevSelectedRef.current = selected.source_id
    const lat = Number(selected.lat)
    const lon = Number(selected.lon)
    if (!isFinite(lat) || !isFinite(lon) || lat === 0 && lon === 0) return
    const currentZoom = map.getZoom()
    const targetZoom  = isFinite(currentZoom) ? Math.max(currentZoom, 17) : 17
    try { map.flyTo([lat, lon], targetZoom, { animate: true, duration: 0.8 }) }
    catch { map.setView([lat, lon], targetZoom) }
  }, [selected, mapReady])

  // Fly to city — только при явной смене пользователем
  const prevCityRef = useRef<string>('')
  useEffect(() => {
    const map = mapObjRef.current
    if (!map || !mapReady) return
    if (prevCityRef.current === cityFilter) return   // инициализация — пропускаем
    prevCityRef.current = cityFilter
    const c = CITY_CENTERS[cityFilter]
    if (!c) return
    try { map.flyTo([c[0], c[1]], c[2], { animate: true, duration: 1 }) }
    catch { map.setView([c[0], c[1]], c[2]) }
  }, [cityFilter, mapReady])

  // ── Геолокация ────────────────────────────────────────────────────────────

  const locate = useCallback(() => {
    const L = leafletRef.current; const map = mapObjRef.current
    if (!L || !map) return
    setLocating(true)
    navigator.geolocation?.getCurrentPosition(
      ({ coords: { latitude: lat, longitude: lng } }) => {
        if (userMarkerRef.current) map.removeLayer(userMarkerRef.current)
        userMarkerRef.current = L.circleMarker([lat, lng], {
          radius: 9, fillColor: '#6366f1', fillOpacity: 1,
          color: '#fff', weight: 3,
          className: 'user-location-dot',
        }).addTo(map).bindTooltip('Вы здесь', { permanent: false })
        try { map.flyTo([lat, lng], 17, { animate: true, duration: 1 }) } catch { map.setView([lat, lng], 17) }
        setLocating(false)
      },
      () => setLocating(false),
      { timeout: 8000, enableHighAccuracy: true }
    )
  }, [])

  // ── Helpers ───────────────────────────────────────────────────────────────

  const typeCounts = Object.keys(TYPE_META).reduce((acc, id) => {
    acc[id] = items.filter(i => i.type.id === id).length
    return acc
  }, {} as Record<string, number>)

  const currentCity = cities.find(c => c.id === cityFilter)

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="absolute inset-0">


      {/* ── КАРТА — z-0, все floating элементы поверх */}
      <div ref={mapContainerRef} className="absolute inset-0" style={{ zIndex: 0 }} />

      {/* ── LEAFLET TOOLTIP CSS ───────────────────────────────────────────── */}
      <style>{`
        .campus-tooltip {
          background: #1e1e24 !important;
          border: 1px solid rgba(255,255,255,0.1) !important;
          border-radius: 8px !important;
          padding: 6px 10px !important;
          box-shadow: 0 4px 16px rgba(0,0,0,0.4) !important;
          color: #e2e8f0 !important;
        }
        .campus-tooltip::before { display: none !important; }
        .leaflet-tooltip-top.campus-tooltip::before { display: none !important; }
        @keyframes pulse-ring {
          0%   { transform: translate(-50%, -60%) scale(0.8); opacity: 1; }
          80%  { transform: translate(-50%, -60%) scale(1.4); opacity: 0; }
          100% { transform: translate(-50%, -60%) scale(1.4); opacity: 0; }
        }
      `}</style>

      {/* Лоадер */}
      {!mapReady && (
        <div className="absolute inset-0 flex items-center justify-center z-50"
          style={{ background: 'var(--card)' }}>
          <Loader2 size={36} className="animate-spin" style={{ color: 'var(--accent)' }} />
        </div>
      )}

      {/* ── Геолокация — floating справа сверху на карте ─────────────────── */}
      <div className="absolute top-4 right-4" style={{ zIndex: 9997 }}>
        <button onClick={locate} disabled={locating}
          className="w-10 h-10 flex items-center justify-center rounded-xl shadow-lg"
          style={{ background: 'var(--card, #1a1a2e)', border: '1px solid var(--border)' }}>
          {locating
            ? <Loader2 size={16} className="animate-spin" style={{ color: 'var(--accent)' }} />
            : <Navigation size={16} style={{ color: 'var(--accent)' }} />
          }
        </button>
      </div>

      {/* ── CITY PILLS (top, below search bar, only on mobile) ───────────── */}
      <div className="absolute top-20 left-3 right-3 z-30 lg:hidden">
        <div className="flex gap-1.5 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
          {cities.map(c => (
            <button key={c.id} onClick={() => setCityFilter(c.id)}
              className="shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold shadow-lg"
              style={{
                background: cityFilter === c.id ? 'var(--accent)' : 'var(--card)',
                color:      cityFilter === c.id ? 'var(--accent-fg)' : 'var(--t-secondary)',
                border:     `1px solid ${cityFilter === c.id ? 'var(--accent)' : 'var(--border)'}`,
              }}>
              {c.title} <span className="opacity-60">{c.total}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── ЛЕВАЯ ПАНЕЛЬ (floating, поверх карты) ────────────────────────── */}
      {sideOpen && (
        <div
          className="absolute top-0 left-0 bottom-0 hidden lg:flex flex-col"
          style={{
            zIndex: 9998,
            width: 320,
            background: 'var(--card, #1a1a2e)',
            borderRight: '1px solid var(--border)',
            boxShadow: '4px 0 24px rgba(0,0,0,0.2)',
          }}
        >
          {/* Заголовок */}
          <div className="px-4 pt-5 pb-3 shrink-0"
            style={{ borderBottom: '1px solid var(--border)' }}>
            <h1 className="text-sm font-bold" style={{ color: 'var(--t-primary)' }}>
              Карта кампусов СКФУ
            </h1>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--t-muted)' }}>
              {isLoading ? '...' : `${items.length} объектов`} · {currentCity?.title ?? 'Все города'}
            </p>
          </div>

          {/* Поиск */}
          <div className="px-3 pt-3 pb-2 shrink-0">
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: 'var(--t-muted)' }} />
              <input
                type="text"
                placeholder="Поиск..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-7 py-2 text-sm rounded-lg"
                style={{
                  background: 'color-mix(in srgb, var(--border, #333) 40%, transparent)',
                  border: '1px solid var(--border, #333)',
                  color: 'var(--t-primary)',
                  outline: 'none',
                }}
              />
              {search && (
                <button onClick={() => setSearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2">
                  <X size={11} style={{ color: 'var(--t-muted)' }} />
                </button>
              )}
            </div>
          </div>

          {/* Город */}
          <div className="px-3 pb-2 shrink-0 flex gap-1.5 overflow-x-auto"
            style={{ scrollbarWidth: 'none' }}>
            {cities.map(c => (
              <button key={c.id} onClick={() => setCityFilter(c.id)}
                className="shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-semibold"
                style={{
                  background: cityFilter === c.id ? 'var(--accent)' : 'var(--card)',
                  color:      cityFilter === c.id ? 'var(--accent-fg)' : 'var(--t-secondary)',
                  border:     `1px solid ${cityFilter === c.id ? 'var(--accent)' : 'var(--border)'}`,
                }}>
                {c.title}
                <span className="opacity-50 ml-0.5">{c.total}</span>
              </button>
            ))}
          </div>

          {/* Тип */}
          <div className="px-3 pb-3 shrink-0 flex gap-1.5 overflow-x-auto"
            style={{ scrollbarWidth: 'none', borderBottom: '1px solid var(--border)' }}>
            <button onClick={() => setTypeFilter('all')}
              className="shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-semibold"
              style={{
                background: typeFilter === 'all' ? 'var(--accent)' : 'transparent',
                color:      typeFilter === 'all' ? 'var(--accent-fg)' : 'var(--t-muted)',
                border:     `1px solid ${typeFilter === 'all' ? 'var(--accent)' : 'var(--border)'}`,
              }}>
              Все
            </button>
            {Object.entries(TYPE_META).map(([id, meta]) => {
              if (!typeCounts[id]) return null
              return (
                <button key={id}
                  onClick={() => setTypeFilter(typeFilter === id ? 'all' : id)}
                  className="shrink-0 px-2.5 py-1 rounded-lg text-[11px] font-semibold"
                  style={{
                    background: typeFilter === id ? meta.markerColor + '25' : 'transparent',
                    color:      typeFilter === id ? meta.markerColor : 'var(--t-muted)',
                    border:     `1px solid ${typeFilter === id ? meta.markerColor + '80' : 'var(--border)'}`,
                  }}>
                  {meta.label} <span className="opacity-60">{typeCounts[id]}</span>
                </button>
              )
            })}
          </div>

          {/* Список */}
          <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
            {isLoading ? (
              <div className="flex justify-center pt-8">
                <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent)' }} />
              </div>
            ) : items.length === 0 ? (
              <p className="px-4 pt-8 text-center text-sm" style={{ color: 'var(--t-muted)' }}>
                Ничего не найдено
              </p>
            ) : (
              items.map(item => {
                const isSelected = selected?.source_id === item.source_id
                const freeRooms  = getFreeRooms(item)
                const meta       = TYPE_META[item.type.id] || TYPE_META.misc
                const Icon       = meta.icon
                return (
                  <button
                    key={item.source_id}
                    id={`row-${item.source_id}`}
                    onClick={() => {
                      const next = isSelected ? null : item
                      setSelected(next)
                      if (next) revealMarker(next.source_id)
                    }}
                    className="w-full text-left flex items-center gap-3 px-4 py-3 transition-colors"
                    style={{
                      background:  isSelected ? `${meta.markerColor}12` : 'transparent',
                      borderLeft:  `2.5px solid ${isSelected ? meta.markerColor : 'transparent'}`,
                    }}
                  >
                    <div className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ background: meta.markerColor + '18', color: meta.markerColor }}>
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold truncate leading-snug"
                        style={{ color: isSelected ? meta.markerColor : 'var(--t-primary)' }}>
                        {item.full_title}
                      </p>
                      <p className="text-[10px] truncate mt-0.5" style={{ color: 'var(--t-muted)' }}>
                        {item.address}
                      </p>
                    </div>
                    {freeRooms !== null && freeRooms.length > 0 && (
                      <span className="shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded"
                        style={{ background: '#10b98118', color: '#10b981' }}>
                        {freeRooms.length}св
                      </span>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}

      {/* ── DETAIL CARD (floating, bottom-right on desktop / bottom sheet mobile) */}
      {selected && (
        <>
          {/* Desktop: карточка справа снизу */}
          <div
            className="absolute bottom-8 right-4 hidden lg:flex flex-col rounded-2xl"
            style={{
              width: 340,
              zIndex: 9999,
              background: 'var(--card, #1a1a2e)',
              border: '1px solid var(--border, #333)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            }}
          >
            {/* Фото */}
            {selected.photo && (
              <div className="relative h-36 overflow-hidden shrink-0">
                <img src={selected.photo} alt={selected.full_title}
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).parentElement!.style.display = 'none' }} />
                <div className="absolute inset-0"
                  style={{ background: 'linear-gradient(to top, var(--card) 0%, transparent 50%)' }} />
              </div>
            )}
            <div className="px-4 pt-3 pb-4 flex flex-col gap-3">
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                      style={{
                        background: (TYPE_META[selected.type.id]?.markerColor ?? '#64748b') + '20',
                        color: TYPE_META[selected.type.id]?.markerColor ?? '#64748b',
                      }}>
                      {selected.type.title}
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
                      {selected.city_title}
                    </span>
                  </div>
                  <h2 className="text-sm font-bold leading-snug" style={{ color: 'var(--t-primary)' }}>
                    {selected.full_title}
                  </h2>
                </div>
                <button onClick={() => setSelected(null)}
                  className="shrink-0 w-7 h-7 flex items-center justify-center rounded-lg"
                  style={{ color: 'var(--t-muted)', background: 'var(--border)' }}>
                  <X size={12} />
                </button>
              </div>

              {/* Адрес + транспорт */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-start gap-2">
                  <MapPin size={12} className="shrink-0 mt-0.5" style={{ color: 'var(--accent)' }} />
                  <p className="text-xs leading-snug" style={{ color: 'var(--t-secondary)' }}>
                    {selected.address}
                  </p>
                </div>
                {selected.transport.bus && (
                  <div className="flex items-start gap-2">
                    <Bus size={12} className="shrink-0 mt-0.5" style={{ color: 'var(--t-muted)' }} />
                    <p className="text-[10px]" style={{ color: 'var(--t-muted)' }}>
                      {selected.transport.bus}
                    </p>
                  </div>
                )}
              </div>

              {/* Свободные аудитории */}
              {(() => {
                const rooms = getFreeRooms(selected)
                if (!rooms || rooms.length === 0) return null
                return (
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5"
                      style={{ color: 'var(--t-muted)' }}>
                      Свободные аудитории
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {rooms.slice(0, 10).map((r: any) => (
                        <button key={r.room_id || r.name}
                          onClick={() => r.room_id && openRoom(r.room_id, r.name)}
                          className="text-[10px] px-2 py-0.5 rounded font-medium"
                          style={{
                            background: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                            color: 'var(--accent)',
                            border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)',
                            cursor: r.room_id ? 'pointer' : 'default',
                          }}>
                          {r.name}
                        </button>
                      ))}
                      {rooms.length > 10 && (
                        <span className="text-[10px] px-2 py-0.5" style={{ color: 'var(--t-muted)' }}>
                          +{rooms.length - 10}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })()}

              {/* Кнопки */}
              <div className="flex gap-2">
                <a href={`https://www.openstreetmap.org/directions?to=${selected.lat},${selected.lon}`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold"
                  style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
                  <Navigation size={12} />Маршрут
                </a>
                <a href={`https://www.openstreetmap.org/?mlat=${selected.lat}&mlon=${selected.lon}&zoom=18`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex items-center justify-center w-9 rounded-xl"
                  style={{ border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
                  <ExternalLink size={13} />
                </a>
              </div>
            </div>
          </div>

          {/* Mobile: bottom sheet */}
          <div
            className="absolute bottom-0 left-0 right-0 lg:hidden rounded-t-2xl"
            style={{
              zIndex: 9999,
              background: 'var(--card, #1a1a2e)',
              borderTop: '1px solid var(--border)',
              paddingBottom: 'env(safe-area-inset-bottom)',
              boxShadow: '0 -8px 32px rgba(0,0,0,0.25)',
            }}
          >
            <div className="flex justify-center pt-2.5 pb-1">
              <div className="w-8 h-1 rounded-full" style={{ background: 'var(--border)' }} />
            </div>
            <div className="px-4 pb-5">
              <div className="flex items-start gap-3 mb-3">
                {selected.photo && (
                  <img src={selected.photo} alt=""
                    className="w-16 h-16 rounded-xl object-cover shrink-0"
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold leading-snug" style={{ color: 'var(--t-primary)' }}>
                    {selected.full_title}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--t-muted)' }}>
                    {selected.address}
                  </p>
                  {selected.transport.bus && (
                    <p className="text-[10px] mt-1" style={{ color: 'var(--t-muted)' }}>
                      🚌 {selected.transport.bus}
                    </p>
                  )}
                </div>
                <button onClick={() => setSelected(null)}
                  className="shrink-0 p-1" style={{ color: 'var(--t-muted)' }}>
                  <X size={16} />
                </button>
              </div>
              <div className="flex gap-2">
                <a href={`https://www.openstreetmap.org/directions?to=${selected.lat},${selected.lon}`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold"
                  style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
                  <Navigation size={14} />Маршрут
                </a>
                <a href={`https://www.openstreetmap.org/?mlat=${selected.lat}&mlon=${selected.lon}&zoom=18`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex items-center justify-center px-4 py-3 rounded-xl"
                  style={{ border: '1px solid var(--border)', color: 'var(--t-secondary)' }}>
                  <ExternalLink size={14} />
                </a>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ── MOBILE BOTTOM TAB BAR ─────────────────────────────────────────── */}
      {!selected && (
        <div className="absolute bottom-0 left-0 right-0 z-30 lg:hidden flex"
          style={{
            background: 'var(--card)',
            borderTop: '1px solid var(--border)',
            paddingBottom: 'env(safe-area-inset-bottom)',
          }}>
          {(['map', 'list'] as const).map(v => (
            <button key={v} onClick={() => setMobileTab(v)}
              className="flex-1 flex items-center justify-center gap-2 py-3 text-sm font-semibold"
              style={{
                color: mobileTab === v ? 'var(--accent)' : 'var(--t-muted)',
                borderTop: `2px solid ${mobileTab === v ? 'var(--accent)' : 'transparent'}`,
              }}>
              {v === 'map' ? <MapIcon size={16} /> : <List size={16} />}
              {v === 'map' ? 'Карта' : 'Список'}
            </button>
          ))}
        </div>
      )}

      {/* ── MOBILE LIST OVERLAY ───────────────────────────────────────────── */}
      {mobileTab === 'list' && !selected && (
        <div className="absolute inset-0 z-30 lg:hidden overflow-y-auto"
          style={{ background: 'var(--card)', paddingBottom: 60 }}>
          {/* Поиск + фильтры */}
          <div className="sticky top-0 z-10 px-4 pt-4 pb-3 flex flex-col gap-2"
            style={{ background: 'var(--card)', borderBottom: '1px solid var(--border)' }}>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: 'var(--t-muted)' }} />
              <input type="text" placeholder="Поиск..." value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-7 py-2 text-sm rounded-lg"
                style={{ background: 'var(--card)', border: '1px solid var(--border)', color: 'var(--t-primary)', outline: 'none' }} />
              {search && <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2"><X size={11} style={{ color: 'var(--t-muted)' }} /></button>}
            </div>
            <div className="flex gap-1.5 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
              {cities.map(c => (
                <button key={c.id} onClick={() => setCityFilter(c.id)}
                  className="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold"
                  style={{
                    background: cityFilter === c.id ? 'var(--accent)' : 'transparent',
                    color:      cityFilter === c.id ? 'var(--accent-fg)' : 'var(--t-muted)',
                    border:     `1px solid ${cityFilter === c.id ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                  {c.title}
                </button>
              ))}
            </div>
          </div>

          {/* Элементы списка */}
          {items.map(item => {
            const meta = TYPE_META[item.type.id] || TYPE_META.misc
            const Icon = meta.icon
            const freeRooms = getFreeRooms(item)
            return (
              <button key={item.source_id}
                onClick={() => { setSelected(item); setMobileTab('map'); revealMarker(item.source_id) }}
                className="w-full text-left flex items-center gap-3 px-4 py-3"
                style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
                  style={{ background: meta.markerColor + '18', color: meta.markerColor }}>
                  <Icon size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: 'var(--t-primary)' }}>
                    {item.full_title}
                  </p>
                  <p className="text-[11px] truncate mt-0.5" style={{ color: 'var(--t-muted)' }}>
                    {item.address}
                  </p>
                </div>
                {freeRooms !== null && freeRooms.length > 0 && (
                  <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded"
                    style={{ background: '#10b98115', color: '#10b981' }}>
                    {freeRooms.length} св.
                  </span>
                )}
                <ChevronRight size={14} style={{ color: 'var(--t-muted)' }} />
              </button>
            )
          })}
        </div>
      )}

    </div>
  )
}
