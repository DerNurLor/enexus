import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, EmptyState, SectionHeader, DetailPanel } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import { fmtDate } from '@/utils/helpers'
import type { Role, Permission } from '@/types'

export function PanelRoles() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [selected, setSelected] = useState<Role | null>(null)
  const [creating, setCreating] = useState(false)
  const qc = useQueryClient()

  const { data: rolesData, isLoading } = useQuery({
    queryKey: ['roles', refreshKey],
    queryFn: () => api.getRoles(),
    staleTime: 30_000,
  })
  const { data: permsData } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => api.getPermissions(),
    staleTime: 60_000,
  })

  const roles = rolesData ?? []
  const allPerms = permsData?.permissions ?? []

  async function deleteRole(r: Role) {
    if (!confirm(`Удалить роль "${r.name}"?`)) return
    try {
      await api.deleteRole(r.id)
      toast.ok('Роль удалена')
      qc.invalidateQueries({ queryKey: ['roles'] })
    } catch (e) { toast.err(extractError(e)) }
  }

  return (
    <div className="anim-up">
      <SectionHeader
        title="Роли и права"
        actions={
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            <Icon.plus /> Создать роль
          </button>
        }
      />

      <div className="grid-2">
        {/* Roles list */}
        <div>
          <div className="card" style={{ padding: 0 }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th style={{ paddingLeft: 16 }}>Роль</th>
                    <th>Прав</th>
                    <th>Создана</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading
                    ? Array.from({ length: 4 }).map((_, i) => (
                        <tr key={i}><td colSpan={4}><div className="skeleton" style={{ height: 10, margin: '9px 16px' }} /></td></tr>
                      ))
                    : roles.map((r) => (
                      <tr key={r.id} onClick={() => setSelected(r)} style={{ cursor: 'pointer' }}>
                        <td style={{ paddingLeft: 16 }}>
                          <div style={{ fontSize: 11, color: 'var(--t-100)' }}>{r.name}</div>
                          {r.description && <div style={{ fontSize: 9, color: 'var(--t-40)' }}>{r.description}</div>}
                        </td>
                        <td style={{ fontSize: 10 }}>{r.permissions.length}</td>
                        <td style={{ fontSize: 9, color: 'var(--t-40)' }}>{fmtDate(r.created_at)}</td>
                        <td>
                          <button className="btn btn-ghost btn-icon" onClick={(e) => { e.stopPropagation(); deleteRole(r) }} title="Удалить">
                            <Icon.trash />
                          </button>
                        </td>
                      </tr>
                    ))
                  }
                </tbody>
              </table>
            </div>
            {!isLoading && !roles.length && <EmptyState text="Нет ролей" />}
          </div>
        </div>

        {/* All permissions reference */}
        <div className="card">
          <div className="card-header"><div className="card-title">Доступные права</div></div>
          {Object.entries(
            allPerms.reduce<Record<string, Permission[]>>((acc, p) => {
              if (!acc[p.group]) acc[p.group] = []
              acc[p.group].push(p)
              return acc
            }, {})
          ).map(([group, perms]) => (
            <div key={group} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: 'var(--t-40)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>{group}</div>
              {perms.map((p) => (
                <div key={p.perm} style={{ padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
                  <div style={{ fontSize: 10, color: 'var(--t-80)', fontFamily: 'var(--mono)' }}>{p.perm}</div>
                  <div style={{ fontSize: 9, color: 'var(--t-40)' }}>{p.description}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {(selected || creating) && (
          <RoleEditor
            role={selected ?? undefined}
            allPerms={allPerms}
            onClose={() => { setSelected(null); setCreating(false) }}
            onSaved={() => { qc.invalidateQueries({ queryKey: ['roles'] }); setSelected(null); setCreating(false) }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function RoleEditor({ role, allPerms, onClose, onSaved }: {
  role?: Role
  allPerms: Permission[]
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(role?.name ?? '')
  const [desc, setDesc] = useState(role?.description ?? '')
  const [perms, setPerms] = useState<string[]>(role?.permissions ?? [])
  const [saving, setSaving] = useState(false)

  function toggle(p: string) {
    setPerms((prev) => prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p])
  }

  async function save() {
    if (!name.trim()) { toast.err('Введите название'); return }
    setSaving(true)
    try {
      if (role) {
        await api.updateRole(role.id, { name: name.trim(), description: desc.trim(), permissions: perms })
        toast.ok('Роль обновлена')
      } else {
        await api.createRole({ name: name.trim(), description: desc.trim(), permissions: perms })
        toast.ok('Роль создана')
      }
      onSaved()
    } catch (e) { toast.err(extractError(e)) }
    setSaving(false)
  }

  return (
    <DetailPanel onClose={onClose}>
      <div className="detail-header">
        <div style={{ flex: 1, fontSize: 12, color: 'var(--t-100)' }}>{role ? `Редактировать: ${role.name}` : 'Новая роль'}</div>
        <button className="btn btn-ghost btn-icon" onClick={onClose}><Icon.close /></button>
      </div>
      <div className="detail-body">
        <div className="input-group" style={{ marginBottom: 10 }}>
          <div className="input-label">Название</div>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="beta_user" />
        </div>
        <div className="input-group" style={{ marginBottom: 16 }}>
          <div className="input-label">Описание</div>
          <input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Описание роли..." />
        </div>
        <div className="input-label" style={{ marginBottom: 8 }}>Права доступа</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 16 }}>
          {allPerms.map((p) => (
            <label key={p.perm} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
              <input type="checkbox" checked={perms.includes(p.perm)} onChange={() => toggle(p.perm)} style={{ accentColor: 'var(--t-80)' }} />
              <div>
                <div style={{ fontSize: 10, color: 'var(--t-80)', fontFamily: 'var(--mono)' }}>{p.perm}</div>
                <div style={{ fontSize: 9, color: 'var(--t-40)' }}>{p.description}</div>
              </div>
            </label>
          ))}
        </div>
        <button className="btn btn-primary w-full" onClick={save} disabled={saving}>
          {saving ? <><Spinner /> Сохранение...</> : `✓ ${role ? 'Обновить' : 'Создать'} роль`}
        </button>
      </div>
    </DetailPanel>
  )
}
