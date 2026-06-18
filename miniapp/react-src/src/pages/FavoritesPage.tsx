import type { Favorite } from '../types'
import { IconGroup, IconTeacher, IconRoom, IconTrash } from '../components/Icons'
import { useI18n } from '../i18n'

interface Props {
  isActive: boolean
  favorites: Favorite[]
  onDelete: (fav: Favorite) => void
  onLoad: (fav: Favorite) => void
}

const TYPE_ICON = {
  group: <IconGroup size={18} />,
  teacher: <IconTeacher size={18} />,
  room: <IconRoom size={18} />,
}

export function FavoritesPage({ favorites, onDelete, onLoad, isActive }: Props) {
  const { t } = useI18n()
  const TYPE_LABEL: Record<string, string> = {
    group: t('common.type_group'),
    teacher: t('common.type_teacher'),
    room: t('common.type_room'),
  }

  return (
    <div id="page-favorites" className={`page${isActive ? " active" : ""}`}>
      <div className="sec-head">{t('favorites.title')}</div>
      <div className="sec-subhead">{t('favorites.subtitle')}</div>

      {favorites.length === 0 ? (
        <>
          <div className="empty-state">
            <div className="empty-icon">☆</div>
            <div className="empty-title">{t('favorites.empty_title')}</div>
            <div className="empty-desc">
              {t('favorites.empty_desc').split('\n').flatMap((line, i, arr) =>
                i < arr.length - 1 ? [line, <br key={i} />] : [line]
              )}
            </div>
          </div>
          <div className="card" style={{ marginTop: 16, textAlign: 'center' }}>
            <span className="text-muted">
              {t('favorites.empty_hint_before')} <strong style={{ color: 'var(--text-secondary)' }}>☆ {t('nav.favorites')}</strong> {t('favorites.empty_hint_after')}
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
                aria-label={t('common.delete')}
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
