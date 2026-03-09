import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { api, extractError } from '@/api/client'
import { useUIStore, toast } from '@/store/ui'
import { Spinner, UserAvatar, EmptyState, SectionHeader } from '@/components/common'
import { Icon } from '@/components/common/Icons'
import { timeAgo, fmtDateTime } from '@/utils/helpers'
import type { ChatMessage, ChatPreview } from '@/types'

const MEDIA_ICONS: Record<string, () => JSX.Element> = {
  photo: Icon.image,
  video: Icon.video,
  animation: Icon.video,
  audio: Icon.audio,
  voice: Icon.audio,
  video_note: Icon.video,
  document: Icon.doc,
  sticker: Icon.sticker,
}

function MediaPreview({ msg, tgId }: { msg: ChatMessage; tgId: number }) {
  const MediaIcon = MEDIA_ICONS[msg.media_type ?? ''] ?? Icon.doc
  const url = msg.file_id ? api.getMediaUrl(tgId, msg.file_id) : undefined

  if (!msg.media_type) return null

  if (msg.media_type === 'photo' && url) {
    return (
      <div style={{ marginBottom: 4 }}>
        <img src={url} alt="photo" style={{ maxWidth: 200, maxHeight: 200, borderRadius: 4, cursor: 'pointer', display: 'block' }}
          onClick={() => window.open(url, '_blank')} />
      </div>
    )
  }
  if ((msg.media_type === 'video' || msg.media_type === 'animation') && url) {
    return (
      <div style={{ marginBottom: 4 }}>
        <video src={url} controls style={{ maxWidth: 200, maxHeight: 200, borderRadius: 4, display: 'block' }} />
      </div>
    )
  }
  if ((msg.media_type === 'audio' || msg.media_type === 'voice') && url) {
    return <audio src={url} controls style={{ width: '100%', marginBottom: 4 }} />
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 0', color: 'var(--t-40)', fontSize: 10, marginBottom: 2 }}>
      <MediaIcon />
      <span>{msg.media_type}{msg.file_name ? ` · ${msg.file_name}` : ''}</span>
    </div>
  )
}

export function PanelChats() {
  const refreshKey = useUIStore((s) => s.refreshKey)
  const [selectedChat, setSelectedChat] = useState<ChatPreview | null>(null)
  const [chatFilter, setChatFilter] = useState('')

  const { data: chatsData, isLoading } = useQuery({
    queryKey: ['chats', refreshKey],
    queryFn: () => api.getChatList(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })

  const chats = (chatsData?.chats ?? []).filter((c) =>
    !chatFilter || c.display.toLowerCase().includes(chatFilter.toLowerCase()) ||
    (c.username ?? '').toLowerCase().includes(chatFilter.toLowerCase())
  )

  return (
    <div className="anim-up" style={{ height: 'calc(100vh - 52px - 44px)', display: 'flex', flexDirection: 'column' }}>
      <SectionHeader title="Чаты" />
      <div className="chat-layout" style={{ flex: 1, overflow: 'hidden' }}>
        {/* Chat list */}
        <div className="chat-list">
          <div className="chat-list-header">
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--t-40)', pointerEvents: 'none' }}><Icon.search /></span>
              <input className="input" style={{ paddingLeft: 28, fontSize: 10 }} placeholder="Поиск..." value={chatFilter} onChange={(e) => setChatFilter(e.target.value)} />
            </div>
          </div>
          <div className="chat-list-body">
            {isLoading
              ? <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}><Spinner /></div>
              : chats.length === 0
              ? <EmptyState text="Чатов нет" />
              : chats.map((c) => (
                <div key={c.tg_id} className={`chat-list-item ${selectedChat?.tg_id === c.tg_id ? 'active' : ''}`}
                  onClick={() => setSelectedChat(c)}>
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--ink-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color: 'var(--t-80)', flexShrink: 0 }}>
                    {(c.display[0] ?? '?').toUpperCase()}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ fontSize: 11, color: c.is_blocked ? 'var(--t-40)' : 'var(--t-80)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }}>{c.display}</span>
                      <span style={{ fontSize: 9, color: 'var(--t-20)', flexShrink: 0 }}>{timeAgo(c.last_ts)}</span>
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--t-40)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.last_text || '—'}</div>
                  </div>
                </div>
              ))
            }
          </div>
        </div>

        {/* Chat messages */}
        {selectedChat
          ? <ChatWindow chat={selectedChat} />
          : <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <EmptyState icon="💬" text="Выберите чат" />
            </div>
        }
      </div>
    </div>
  )
}

function ChatWindow({ chat }: { chat: ChatPreview }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [reply, setReply] = useState('')
  const [search, setSearch] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<ChatMessage[] | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastTs = useRef<string>()
  const LIMIT = 30

  async function loadHistory(off = 0) {
    setLoading(true)
    try {
      const d = await api.getChatHistory(chat.tg_id, { offset: off, limit: LIMIT })
      setMessages(d.messages.reverse())
      setTotal(d.total)
      setOffset(off)
      if (d.messages[0]) lastTs.current = d.messages[0].timestamp
    } catch (e) { toast.err(extractError(e)) }
    setLoading(false)
  }

  useEffect(() => { loadHistory(0); setSearchResults(null) }, [chat.tg_id])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages.length])

  // Polling for new messages every 5s
  useEffect(() => {
    const t = setInterval(async () => {
      try {
        const d = await api.pollChat(chat.tg_id, lastTs.current)
        if (d.messages.length > 0) {
          setMessages((prev) => {
            const seen = new Set(prev.map((m) => m.message_id))
            const fresh = d.messages.filter((m) => !seen.has(m.message_id))
            if (!fresh.length) return prev
            if (fresh[fresh.length - 1]) lastTs.current = fresh[fresh.length - 1].timestamp
            return [...prev, ...fresh]
          })
        }
      } catch {}
    }, 5000)
    return () => clearInterval(t)
  }, [chat.tg_id])

  async function sendReply() {
    if (!reply.trim()) return
    setSending(true)
    try {
      await api.sendMessage(chat.tg_id, reply.trim())
      setReply('')
      toast.ok('Отправлено')
      await loadHistory(0)
    } catch (e) { toast.err(extractError(e)) }
    setSending(false)
  }

  async function doSearch() {
    if (!search.trim()) { setSearchResults(null); return }
    setSearching(true)
    try {
      const d = await api.searchChat(chat.tg_id, search.trim())
      setSearchResults(d.messages)
    } catch (e) { toast.err(extractError(e)) }
    setSearching(false)
  }

  const displayMessages = searchResults ?? messages

  return (
    <div className="chat-main">
      {/* Chat header */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: 'var(--t-100)' }}>{chat.display}</div>
          <div style={{ fontSize: 9, color: 'var(--t-40)' }}>tg:{chat.tg_id} · {total} сообщений</div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <input className="input" style={{ width: 140, fontSize: 10 }} placeholder="Поиск..." value={search}
            onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && doSearch()} />
          {searching && <Spinner />}
          {searchResults && <button className="btn btn-ghost btn-icon" onClick={() => { setSearchResults(null); setSearch('') }}><Icon.close /></button>}
        </div>
      </div>

      {/* Messages */}
      <div className="chat-msgs">
        {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}><Spinner /></div>
          : displayMessages.length === 0 ? <EmptyState text="Нет сообщений" />
          : displayMessages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.role === 'bot' || msg.role === 'assistant' ? 'bot' : msg.role === 'admin' ? 'admin' : ''}`}>
              <div className={`msg-bubble ${msg.role === 'bot' || msg.role === 'assistant' ? 'bot' : msg.role === 'admin' ? 'admin' : 'user'}`}>
                {msg.is_forward && <div style={{ fontSize: 9, color: 'var(--t-40)', marginBottom: 4 }}>↪ {msg.forward_from_name ?? 'Forwarded'}</div>}
                {msg.reply_to_text && <div style={{ fontSize: 9, color: 'var(--t-40)', borderLeft: '2px solid var(--line3)', paddingLeft: 6, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', maxHeight: 32, whiteSpace: 'nowrap' }}>{msg.reply_to_text}</div>}
                <MediaPreview msg={msg} tgId={chat.tg_id} />
                {msg.text && <div style={{ lineHeight: 1.5 }} dangerouslySetInnerHTML={{ __html: msg.html_text || msg.text }} />}
                <div className="msg-meta">{fmtDateTime(msg.timestamp)}</div>
              </div>
            </div>
          ))
        }
        <div ref={bottomRef} />
      </div>

      {/* Reply input */}
      <div className="chat-input">
        <textarea className="input" style={{ flex: 1, minHeight: 36, maxHeight: 120, resize: 'none' }}
          placeholder="Написать сообщение..." value={reply}
          onChange={(e) => setReply(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendReply() } }} />
        <button className="btn btn-primary" onClick={sendReply} disabled={sending || !reply.trim()}>
          {sending ? <Spinner /> : <Icon.send />}
        </button>
      </div>
    </div>
  )
}
