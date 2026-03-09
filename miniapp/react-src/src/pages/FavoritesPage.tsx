import type { Favorite } from '../types'
import { IconGroup, IconTeacher, IconRoom, IconTrash } from '../components/Icons'

interface Props {
  isActive: boolean
  favorites: Favorite[]
  onDelete: (fav: Favorite) => void
  onLoad: (fav: Favorite) => void
}

const TYPE_LABEL: Record<string, string> = {
  group: 'Группа',
  teacher: 'Преподаватель',
  room: 'Аудитория',
}

const TYPE_ICON = {
  group: <IconGroup size={18} />,
  teacher: <IconTeacher size={18} />,
  room: <IconRoom size={18} />,
}

export function FavoritesPage({ favorites, onDelete, onLoad, isActive }: Props) {
  return (
    <div id="page-favorites" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">ИЗБРАННОЕ</div>
      <div className="sec-subhead">Быстрый доступ к группам и преподавателям</div>

      {favorites.length === 0 ? (
        <>
          <div className="empty-state">
            <div className="empty-icon">☆</div>
            <div className="empty-title">ПУСТО</div>
            <div className="empty-desc">
              Сохраните группу, преподавателя<br />или аудиторию для быстрого доступа
            </div>
          </div>
          <div className="card" style={{ marginTop: 16, textAlign: 'center' }}>
            <span className="text-muted">
              Нажмите <strong style={{ color: 'var(--text-secondary)' }}>☆ Избранное</strong> в результатах поиска
            </span>
          </div>
        </>
      ) : (
        <>
          {favorites.map((f, i) => (
            <div
              key={`${f.type}:${f.id}`}
              className="fav-card"
              style={{ animationDelay: `${i * 0.05}s` }}
              onClick={() => onLoad(f)}
            >
              <div className="fav-icon">
                {TYPE_ICON[f.type] ?? <IconGroup size={18} />}
              </div>
              <div className="fav-info">
                <div className="fav-name">{f.label}</div>
                <div className="fav-type">{TYPE_LABEL[f.type] ?? f.type}</div>
              </div>
              <button
                className="fav-del"
                onClick={e => { e.stopPropagation(); onDelete(f) }}
                aria-label="Удалить"
              >
                <IconTrash size={15} />
              </button>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
