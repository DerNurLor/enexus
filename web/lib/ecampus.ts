/**
 * Загружает предметы + зачётку через GraphQL (myEcampus) вместо тяжёлого
 * REST GET /ecampus/data (отдавал сырые занятия каждого курса — 1-2 минуты
 * на холодный кэш). Курсы приходят без занятий, рейтинг посчитан на сервере.
 * Используется и /ecampus, и /profile — оба читают один queryKey ['ecampus-data'].
 *
 * Запрос разбит на несколько параллельных GraphQL-запросов — один на учебный
 * год (см. myEcampusYears + termIds-фильтр на myEcampus), вместо одного
 * большого запроса на все курсы сразу. Это позволяет браузеру и серверу
 * обрабатывать года параллельно и не ждать самый медленный путь целиком.
 *
 * Ответ адаптирован в форму старого REST-блоба, чтобы потребители (поиск,
 * группировка по семестрам, фильтры LessonType, ZachetkaModal/StatsModal,
 * updateGradeSnapshot) не менялись.
 *
 * Кэш в браузере (localStorage): результат сохраняется и на следующий холодный
 * старт отдаётся мгновенно (см. getCachedEcampusOverview, используется как
 * placeholderData), а свежий ответ GraphQL не просто заменяет кэш целиком, а
 * мерджится — новые предметы добавляются, существующие обновляются, и ничего
 * не пропадает из-за временно неполного ответа (тот же принцип, что и на
 * сервере в sync_service.py). Удаление из кэша происходит только когда ВСЕ
 * параллельные запросы отработали успешно И сервер подтвердил sync_status='ok'.
 */

const CACHE_KEY = 'ncfu_ecampus_cache'
const MAX_PARALLEL_FETCHES = 5
// Сколько из них реально летят одновременно — см. runWithConcurrencyLimit.
const CONCURRENCY_LIMIT = 3

const GRAPHQL_URL = (process.env.NEXT_PUBLIC_API_URL || '') + '/api/graphql'

function courseKey(c: any): string {
  return `${c.Id}_${c.term_id}`
}

function readCache(): any | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function writeCache(data: any) {
  if (typeof window === 'undefined') return
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(data)) } catch { /* quota / приватный режим — не критично */ }
}

/** Очищает кэш предметов — вызывать при logout и при отключении eCampus. */
export function clearEcampusCache() {
  if (typeof window === 'undefined') return
  try { localStorage.removeItem(CACHE_KEY) } catch { /* */ }
}

/** Синхронный доступ к последнему сохранённому снимку — для placeholderData на холодном старте. */
export function getCachedEcampusOverview() {
  return readCache()
}

function mergeOverview(prev: any | null, fresh: any, allowRemoval: boolean) {
  if (!prev?.courses?.length) return fresh

  const merged = new Map<string, any>()
  for (const c of prev.courses) merged.set(courseKey(c), c)
  for (const c of fresh.courses || []) merged.set(courseKey(c), c) // добавление + обновление

  let courses: any[]
  if (allowRemoval && fresh.sync_status === 'ok') {
    // Все части запроса отработали и синхронизация подтверждённо завершена —
    // список от сервера авторитетный, предметы, которых там больше нет, убираем.
    const freshKeys = new Set((fresh.courses || []).map(courseKey))
    courses = [...merged.values()].filter(c => freshKeys.has(courseKey(c)))
  } else {
    // Идёт синхронизация, ошибка, или часть параллельных запросов не удалась —
    // ответ может быть неполным, ничего не теряем.
    courses = [...merged.values()]
  }

  return { ...fresh, courses }
}

const CHUNK_TIMEOUT_MS = 10_000

async function graphqlRequest(token: string, query: string, timeoutMs = CHUNK_TIMEOUT_MS): Promise<any | null> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(GRAPHQL_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query }),
      signal: ctrl.signal,
    })
    if (!res.ok) return null
    const json = await res.json()
    if (json.errors?.length) return null
    return json.data
  } catch {
    // Таймаут или сетевая ошибка — пусть вызывающий код упадёт обратно на кэш
    // для этого куска, а не подвешивает весь экран на десятки секунд.
    return null
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Запускает асинхронные задачи с ограничением одновременных — на медленной/мобильной
 * сети 5 параллельных TLS-соединений разом могут конкурировать друг с другом и каждое
 * выполняться дольше, чем если бы они шли по 2-3. limit ограничивает одновременные.
 */
async function runWithConcurrencyLimit<T>(tasks: (() => Promise<T>)[], limit: number): Promise<T[]> {
  const results: T[] = new Array(tasks.length)
  let next = 0
  async function worker() {
    while (next < tasks.length) {
      const i = next++
      results[i] = await tasks[i]()
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, worker))
  return results
}

function adaptCourse(c: any) {
  return {
    Id:           c.id,
    Name:         c.name,
    term_id:      c.termId,
    term_name:    c.termName,
    LessonTypes:  (c.lessonTypes || []).map((lt: any) => ({ Id: lt.id, Name: lt.name, LessonType: lt.lessonType })),
    ratingGained: c.ratingGained,
    ratingMax:    c.ratingMax,
    // Алиасы под старые имена полей eCampus — нужны StatsModal (термы/рейтинг по предметам)
    CurrentRating: c.ratingGained,
    MaxRating:     c.ratingMax,
    gradeCount:   (c.gradedLessons || []).length,
    // Минимальная форма lessons — только для updateGradeSnapshot (нужны Id + GradeText)
    lessons: (c.gradedLessons || []).length ? { _: c.gradedLessons.map((g: any) => ({ Id: g.id, GradeText: g.gradeText })) } : {},
  }
}

/** Один запрос за подмножество термов (или за все, если termIds не задан). */
async function fetchOverviewChunk(token: string, termIds: number[] | null, includeZachetka: boolean) {
  const args = termIds ? `(termIds: [${termIds.join(',')}])` : ''
  const query = `query MyEcampus {
    myEcampus${args} {
      syncStatus
      lastSync
      ${includeZachetka ? 'zachetka' : ''}
      courses {
        id name termId termName
        ratingGained ratingMax
        lessonTypes { id name lessonType }
        gradedLessons { id gradeText }
      }
    }
  }`
  const data = await graphqlRequest(token, query)
  if (!data?.myEcampus) return null
  const d = data.myEcampus
  return {
    sync_status: d.syncStatus as string,
    last_sync:   d.lastSync as string | null,
    zachetka:    includeZachetka ? (d.zachetka || {}) : undefined,
    courses:     (d.courses || []).map(adaptCourse),
  }
}

/** Группирует года в максимум maxChunks подмножеств term_id (распределяя по количеству курсов). */
function chunkYears(years: { year: string; termIds: number[]; courseCount: number }[], maxChunks: number): number[][] {
  if (years.length <= maxChunks) return years.map(y => y.termIds).filter(t => t.length)

  const chunks: number[][] = Array.from({ length: maxChunks }, () => [])
  const chunkLoads = Array(maxChunks).fill(0)
  const sorted = [...years].sort((a, b) => b.courseCount - a.courseCount)
  for (const y of sorted) {
    const minIdx = chunkLoads.indexOf(Math.min(...chunkLoads))
    chunks[minIdx].push(...y.termIds)
    chunkLoads[minIdx] += y.courseCount
  }
  return chunks.filter(c => c.length > 0)
}

export async function fetchEcampusOverview() {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  if (!token) return null

  // 1. Лёгкие метаданные — сколько годов и какие term_id у каждого.
  const yearsData = await graphqlRequest(token, `query { myEcampusYears { year termIds courseCount } }`)
  const years = yearsData?.myEcampusYears as { year: string; termIds: number[]; courseCount: number }[] | undefined

  if (!years?.length) {
    // Синхронизации ещё не было либо курсов нет вообще — обычный единый запрос.
    const chunk = await fetchOverviewChunk(token, null, true)
    if (!chunk) return readCache()
    const merged = mergeOverview(readCache(), chunk, true)
    writeCache(merged)
    return merged
  }

  // 2. До 4-5 запросов — один на учебный год (или группу годов, если их больше),
  // но не более CONCURRENCY_LIMIT одновременно — иначе на медленной/мобильной сети
  // несколько параллельных TLS-соединений начинают конкурировать друг с другом и
  // КАЖДОЕ выполняется дольше, чем если бы они шли мелкими волнами.
  const chunks = chunkYears(years, MAX_PARALLEL_FETCHES)
  const results = await runWithConcurrencyLimit(
    chunks.map((termIds, i) => () => fetchOverviewChunk(token, termIds, i === 0)),
    CONCURRENCY_LIMIT,
  )

  const succeeded = results.filter((r): r is NonNullable<typeof r> => r !== null)
  if (!succeeded.length) return readCache()

  const first = succeeded.find(r => r.zachetka !== undefined) ?? succeeded[0]
  const fresh = {
    sync_status: first.sync_status,
    last_sync:   first.last_sync,
    zachetka:    first.zachetka ?? readCache()?.zachetka ?? {},
    courses:     succeeded.flatMap(r => r.courses),
  }

  const allowRemoval = succeeded.length === results.length // все части отработали
  const merged = mergeOverview(readCache(), fresh, allowRemoval)
  writeCache(merged)
  return merged
}

// ── Данные одного предмета (раньше REST /course/{id}/lessons и /materials) ────

export async function fetchCourseLessons(courseId: number, termId: number, groupId: number | null) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  if (!token) throw new Error('401')

  const args = `courseId: ${courseId}, termId: ${termId}${groupId ? `, groupId: ${groupId}` : ''}`
  const query = `query { myEcampusCourseLessons(${args}) { courseId courseName lessons maxRating currentRating } }`
  const data = await graphqlRequest(token, query)
  if (!data?.myEcampusCourseLessons) throw new Error('GraphQL request failed')
  const d = data.myEcampusCourseLessons
  return {
    course_id:      d.courseId,
    course_name:    d.courseName,
    lessons:        d.lessons,
    max_rating:     d.maxRating,
    current_rating: d.currentRating,
  }
}

export async function fetchCourseMaterials(courseId: number, termId: number) {
  const { getToken } = await import('@/lib/auth')
  const token = getToken()
  if (!token) throw new Error('401')

  const query = `query { myEcampusCourseMaterials(courseId: ${courseId}, termId: ${termId}) { label url icon external color } }`
  const data = await graphqlRequest(token, query)
  if (!data) throw new Error('GraphQL request failed')
  return { materials: data.myEcampusCourseMaterials || [] }
}
