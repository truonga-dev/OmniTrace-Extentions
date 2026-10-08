import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API = 'http://localhost:8000'

type Mode = 'username' | 'email' | 'name' | 'image'
type Status = 'confirmed' | 'registered' | 'unverified' | 'search'
type Phase = 'idle' | 'scanning' | 'results' | 'error'

interface TraceResult {
  platform: string
  url?: string | null
  username?: string | null
  status: Status
  category: 'account' | 'search' | 'metadata'
  source: string
  note?: string | null
  details?: Record<string, string> | null
}

interface Profile {
  name?: string | null
  avatar?: string | null
  bio?: string | null
  location?: string | null
  source?: string | null
}

interface TraceResponse {
  query: string
  type: Mode
  results: TraceResult[]
  profile?: Profile | null
  metadata?: Record<string, string>
  stats: { checked: number; found: number; duration: number }
  warnings: string[]
}

const MODES: Record<Mode, { label: string; placeholder: string; hint: string; sources: string; eta: string; examples: string[] }> = {
  username: {
    label: 'Username / ID',
    placeholder: 'vd: torvalds, @user hoặc link hồ sơ',
    hint: 'Kiểm tra tài khoản có tồn tại trên 500 trang phổ biến bằng quy tắc nhận diện riêng của từng trang.',
    sources: 'Maigret · 500 trang (GitHub, TikTok, Facebook, Reddit, Telegram, Twitch...)',
    eta: '1–2 phút',
    examples: ['torvalds', 'gaearon'],
  },
  email: {
    label: 'Email',
    placeholder: 'vd: ten@gmail.com',
    hint: 'Kiểm tra email đã đăng ký trên trang nào. Không thể biết username trên trang đó vì trang không công khai.',
    sources: 'holehe · 120+ trang · hồ sơ Gravatar công khai',
    eta: '15–30 giây',
    examples: ['test@gmail.com'],
  },
  name: {
    label: 'Họ tên',
    placeholder: 'vd: Nguyễn Văn A',
    hint: 'Họ tên không phải định danh duy nhất. Kết quả là ứng viên + liên kết tìm kiếm, cần tự xác minh.',
    sources: 'GitHub user search · liên kết tìm người trên Facebook, LinkedIn, X, TikTok...',
    eta: 'vài giây',
    examples: ['Linus Torvalds'],
  },
  image: {
    label: 'Hình ảnh',
    placeholder: 'hoặc dán URL ảnh: https://...',
    hint: 'Đọc metadata (thiết bị, thời gian, GPS) và tìm ngược ảnh để xem trang nào đã đăng ảnh. Không nhận diện khuôn mặt.',
    sources: 'EXIF · Google Lens · Yandex · Bing · TinEye',
    eta: '5–15 giây',
    examples: [],
  },
}

const STATUS_META: Record<Status, { label: string; badge: string; section: string; desc: string }> = {
  confirmed: { label: 'Xác nhận', badge: 'Đã xác nhận', section: 'Tài khoản đã xác nhận', desc: 'Trang xác nhận tài khoản tồn tại' },
  registered: { label: 'Đã đăng ký', badge: 'Đã đăng ký', section: 'Email đã đăng ký', desc: 'Email đã được dùng trên trang này' },
  unverified: { label: 'Cần xác minh', badge: 'Cần xác minh', section: 'Cần xác minh thủ công', desc: 'Có thể đúng, hãy mở để kiểm tra' },
  search: { label: 'Tìm kiếm', badge: 'Tìm kiếm', section: 'Liên kết tìm kiếm', desc: 'Mở để tự tìm kiếm' },
}
const STATUS_ORDER: Status[] = ['confirmed', 'registered', 'unverified', 'search']

const PLATFORM_DOMAINS: Record<string, string> = {
  instagram: 'instagram.com', facebook: 'facebook.com', 'x (twitter)': 'x.com', twitter: 'x.com',
  tiktok: 'tiktok.com', linkedin: 'linkedin.com', youtube: 'youtube.com', github: 'github.com',
  google: 'google.com', 'google maps': 'maps.google.com', 'google lens': 'lens.google.com',
  'yandex images': 'yandex.com', 'bing visual search': 'bing.com', tineye: 'tineye.com', gravatar: 'gravatar.com',
}

function domainFor(r: TraceResult): string | null {
  const known = PLATFORM_DOMAINS[r.platform.toLowerCase()]
  if (known) return known
  try { return r.url ? new URL(r.url).hostname.replace(/^www\./, '') : null } catch { return null }
}

function PlatformIcon({ result }: { result: TraceResult }) {
  const [failed, setFailed] = useState(false)
  const domain = domainFor(result)
  if (!domain || failed) {
    return <div className="res-icon res-icon-fallback">{result.platform.slice(0, 1).toUpperCase()}</div>
  }
  return (
    <div className="res-icon">
      <img src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`} alt="" onError={() => setFailed(true)} />
    </div>
  )
}

function ResultItem({ r }: { r: TraceResult }) {
  const [open, setOpen] = useState(false)
  const hasDetails = !!r.details && Object.keys(r.details).length > 0
  const subtitle = r.username ? `@${r.username}` : r.url?.replace(/^https?:\/\/(www\.)?/, '')
  return (
    <div className={`result-item status-${r.status}`}>
      <div className="res-row">
        <PlatformIcon result={r} />
        <div className="res-info">
          <div className="res-title">
            <span className="res-name">{r.platform}</span>
            <span className={`badge badge-${r.status}`}>{STATUS_META[r.status].badge}</span>
          </div>
          {subtitle && <span className="res-desc" title={r.url ?? ''}>{subtitle}</span>}
          {r.note && <span className="res-note">{r.note}</span>}
        </div>
        <div className="res-actions">
          {hasDetails && (
            <button className="icon-btn" onClick={() => setOpen(!open)} title="Chi tiết">{open ? '−' : '+'}</button>
          )}
          {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="res-link">Mở</a>}
        </div>
      </div>
      {open && hasDetails && (
        <dl className="res-details">
          {Object.entries(r.details!).map(([k, v]) => (
            <div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>
          ))}
        </dl>
      )}
    </div>
  )
}

function App() {
  const [mode, setMode] = useState<Mode>('username')
  const [query, setQuery] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [data, setData] = useState<TraceResponse | null>(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState<Status | 'all'>('all')
  const [elapsed, setElapsed] = useState(0)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Backend health indicator
  useEffect(() => {
    const check = () =>
      fetch(`${API}/api/health`).then(r => setApiOnline(r.ok)).catch(() => setApiOnline(false))
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  // Elapsed timer while scanning
  useEffect(() => {
    if (phase !== 'scanning') return
    setElapsed(0)
    const id = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(id)
  }, [phase])

  useEffect(() => () => { if (imagePreview) URL.revokeObjectURL(imagePreview) }, [imagePreview])

  const pickFile = (f: File | null) => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImageFile(f)
    setImagePreview(f ? URL.createObjectURL(f) : null)
  }

  const canSubmit = mode === 'image' ? !!imageFile || /^https?:\/\//.test(query.trim()) : query.trim().length > 0

  const runTrace = async () => {
    if (!canSubmit) return
    const controller = new AbortController()
    abortRef.current = controller
    setPhase('scanning')
    setFilter('all')
    setError('')
    try {
      let res: Response
      if (mode === 'image') {
        const form = new FormData()
        if (imageFile) form.append('file', imageFile)
        else form.append('url', query.trim())
        res = await fetch(`${API}/api/trace/image`, { method: 'POST', body: form, signal: controller.signal })
      } else {
        res = await fetch(`${API}/api/trace`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: mode, query: query.trim() }),
          signal: controller.signal,
        })
      }
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || `Lỗi máy chủ (${res.status})`)
      setData(json)
      setPhase('results')
    } catch (e) {
      if ((e as Error).name === 'AbortError') { setPhase('idle'); return }
      setError(e instanceof TypeError
        ? 'Không kết nối được backend. Hãy chạy: uvicorn main:app --reload (thư mục backend).'
        : (e as Error).message)
      setPhase('error')
    }
  }

  const reset = () => { setPhase('idle'); setData(null); setError('') }

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: data?.results.length ?? 0 }
    for (const s of STATUS_ORDER) c[s] = data?.results.filter(r => r.status === s).length ?? 0
    return c
  }, [data])

  const exportJson = () => {
    if (!data) return
    const exportData = {
      ...data,
      linkedin: linkedinData
    }
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `omnitrace_${data.type}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const exportCsv = () => {
    if (!data) return
    const rows = [
      ['Nền tảng', 'Trạng thái', 'Username/URL', 'Ghi chú']
    ]
    data.results.forEach(r => {
      const subtitle = r.username ? `@${r.username}` : r.url ?? ''
      rows.push([r.platform, STATUS_META[r.status].label, subtitle, r.note ?? ''])
    })
    
    // Nếu có dữ liệu LinkedIn
    if (linkedinData) {
       rows.push(['---', '---', '---', '---'])
       rows.push(['Dữ liệu LinkedIn', '', '', ''])
       if (linkedinData.type === 'profile') {
          rows.push(['Tên', '', linkedinData.name || '', ''])
          rows.push(['Chức vụ', '', linkedinData.headline || '', ''])
          rows.push(['Công ty', '', linkedinData.company || '', ''])
       } else if (linkedinData.type === 'search' && linkedinData.profiles) {
          linkedinData.profiles.forEach((p: any) => {
             rows.push(['Kết quả tìm kiếm', '', p.name || '', p.headline || ''])
          })
       }
    }

    const csvContent = rows.map(e => e.map(item => `"${String(item).replace(/"/g, '""')}"`).join(",")).join("\n")
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `omnitrace_${data.type}_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const [linkedinData, setLinkedinData] = useState<any>(null)

  const scrapeCurrentTab = () => {
    if (typeof chrome === 'undefined' || !chrome.tabs) return;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0 && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "SCRAPE_LINKEDIN" }, (response) => {
          if (chrome.runtime.lastError) {
             console.error("Không thể kết nối với content script:", chrome.runtime.lastError.message);
             return;
          }
          if (response && response.success) {
             setLinkedinData(response.data);
          }
        });
      }
    });
  }

  const cfg = MODES[mode]
  const scanSteps: Record<Mode, string[]> = {
    username: ['Chuẩn hoá username', 'Tải cơ sở dữ liệu 500 trang', 'Gửi truy vấn song song', 'Áp dụng quy tắc nhận diện từng trang', 'Trích xuất thông tin hồ sơ'],
    email: ['Kiểm tra định dạng email', 'Truy vấn hồ sơ Gravatar', 'Kiểm tra đăng ký trên 120+ trang', 'Lọc kết quả bị chặn tần suất'],
    name: ['Chuẩn hoá họ tên', 'Tìm ứng viên trên GitHub', 'Tạo liên kết tìm người'],
    image: ['Đọc metadata EXIF', 'Tải ảnh lên công cụ tìm ngược', 'Tạo liên kết kết quả'],
  }
  const steps = scanSteps[mode]
  const activeStep = Math.min(steps.length - 1, Math.floor(elapsed / (mode === 'username' ? 15 : 3)))

  return (
    <div className="app-container">
      <header className="header-section">
        <div className="brand-group">
          <div className="logo-container"><img src="/icon.png" alt="OmniTrace" className="logo-img" /></div>
          <h1 className="brand-name">Omni<span className="brand-trace">Trace</span></h1>
        </div>
        <div className={`status-badge ${apiOnline === false ? 'offline' : ''}`} title={API}>
          <span className="status-dot" />
          {apiOnline === null ? 'Đang kiểm tra' : apiOnline ? 'Backend online' : 'Backend offline'}
        </div>
      </header>

      <main className="content-section">
        {phase === 'idle' && (
          <>
            <div className="search-tabs">
              {(Object.keys(MODES) as Mode[]).map(m => (
                <button key={m} className={`tab-btn ${mode === m ? 'active' : ''}`}
                  onClick={() => { setMode(m); setQuery('') }}>
                  {MODES[m].label}
                </button>
              ))}
            </div>

            {mode === 'image' && (
              <div
                className={`dropzone ${imagePreview ? 'has-image' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f?.type.startsWith('image/')) pickFile(f) }}
              >
                {imagePreview ? (
                  <>
                    <img src={imagePreview} alt="preview" />
                    <button className="dropzone-clear" onClick={e => { e.stopPropagation(); pickFile(null) }}>×</button>
                  </>
                ) : (
                  <span>Kéo thả ảnh vào đây hoặc <b>bấm để chọn</b><br /><small>JPG, PNG, WEBP · tối đa 10MB</small></span>
                )}
                <input ref={fileInputRef} type="file" accept="image/*" hidden
                  onChange={e => pickFile(e.target.files?.[0] ?? null)} />
              </div>
            )}

            {!(mode === 'image' && imageFile) && (
              <div className="input-wrapper">
                <svg className="input-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                <input
                  type={mode === 'email' ? 'email' : 'text'}
                  className="custom-input"
                  placeholder={cfg.placeholder}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && runTrace()}
                  autoFocus
                />
              </div>
            )}

            {cfg.examples.length > 0 && (
              <div className="quick-chips">
                <span className="chips-label">Thử:</span>
                {cfg.examples.map(ex => <span key={ex} className="chip" onClick={() => setQuery(ex)}>{ex}</span>)}
              </div>
            )}

            <div className="info-card">
              <p className="info-hint">{cfg.hint}</p>
              <div className="info-row"><span>Nguồn dữ liệu</span><b>{cfg.sources}</b></div>
              <div className="info-row"><span>Thời gian dự kiến</span><b>{cfg.eta}</b></div>
            </div>

            <button className="btn-primary" disabled={!canSubmit || apiOnline === false} onClick={runTrace}>
              Bắt đầu truy vết
            </button>

            {typeof chrome !== 'undefined' && chrome.tabs && (
              <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <button className="btn-secondary" onClick={scrapeCurrentTab}>
                  Lấy dữ liệu từ tab LinkedIn hiện tại
                </button>
                {linkedinData && (
                  <div className="info-card" style={{ marginTop: '0' }}>
                    <div className="info-row">
                      <span>Trạng thái</span>
                      <b>
                        {linkedinData.type === 'profile' 
                          ? `Đã lấy: ${linkedinData.name || 'Không rõ tên'} ${linkedinData.company ? `- ${linkedinData.company}` : ''}`
                          : linkedinData.type === 'search'
                            ? `Đã lấy danh sách tìm kiếm (${linkedinData.profiles?.length || 0} kết quả)`
                            : 'Không tìm thấy dữ liệu LinkedIn'}
                      </b>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {phase === 'scanning' && (
          <div className="scan-view">
            <div className="scan-header">
              <div className="spinner" />
              <div>
                <div className="scan-title">Đang truy vết <b>{mode === 'image' ? (imageFile?.name ?? 'ảnh') : query}</b></div>
                <div className="scan-sub">{elapsed}s · dự kiến {cfg.eta}</div>
              </div>
            </div>
            <ol className="scan-steps">
              {steps.map((s, i) => (
                <li key={s} className={i < activeStep ? 'done' : i === activeStep ? 'active' : ''}>{s}</li>
              ))}
            </ol>
            <button className="btn-secondary" onClick={() => abortRef.current?.abort()}>Huỷ</button>
          </div>
        )}

        {phase === 'error' && (
          <div className="error-view">
            <div className="error-icon">!</div>
            <p>{error}</p>
            <button className="btn-secondary" onClick={reset}>Quay lại</button>
          </div>
        )}

        {phase === 'results' && data && (
          <>
            <div className="result-overview">
              <div className="res-target" title={data.query}>{data.query}</div>
              <div className="stats-row">
                <span><b>{data.stats.checked}</b> nguồn đã kiểm tra</span>
                <span><b>{data.stats.found}</b> kết quả</span>
                <span><b>{data.stats.duration}s</b></span>
              </div>
            </div>

            {data.profile && (
              <div className="profile-card">
                {data.profile.avatar && <img src={data.profile.avatar} alt="" className="profile-avatar" />}
                <div className="profile-info">
                  {data.profile.name && <div className="profile-name">{data.profile.name}</div>}
                  {data.profile.location && <div className="profile-meta">📍 {data.profile.location}</div>}
                  {data.profile.bio && <div className="profile-bio">{data.profile.bio}</div>}
                  {data.profile.source && <div className="profile-source">Nguồn: {data.profile.source}</div>}
                </div>
              </div>
            )}

            {data.metadata && Object.keys(data.metadata).length > 0 && (
              <div className="meta-card">
                <div className="section-title">Metadata ảnh</div>
                <dl className="res-details">
                  {Object.entries(data.metadata).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
                </dl>
              </div>
            )}

            {data.warnings.length > 0 && (
              <div className="warning-box">
                {data.warnings.map(w => <div key={w}>⚠ {w}</div>)}
              </div>
            )}

            {data.results.length === 0 ? (
              <div className="empty-state">
                <p>Không tìm thấy tài khoản nào.</p>
                <small>Đã kiểm tra {data.stats.checked} nguồn, không có kết quả trùng khớp.</small>
              </div>
            ) : (
              <>
                <div className="filter-row">
                  <button className={`filter-chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>Tất cả {counts.all}</button>
                  {STATUS_ORDER.filter(s => counts[s] > 0).map(s => (
                    <button key={s} className={`filter-chip chip-${s} ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
                      {STATUS_META[s].label} {counts[s]}
                    </button>
                  ))}
                </div>

                {STATUS_ORDER.filter(s => (filter === 'all' || filter === s) && counts[s] > 0).map(s => (
                  <section key={s} className="result-section">
                    <div className="section-title">
                      {STATUS_META[s].section} <span>· {STATUS_META[s].desc}</span>
                    </div>
                    <div className="result-list">
                      {data.results.filter(r => r.status === s).map((r, i) => <ResultItem key={`${r.platform}-${i}`} r={r} />)}
                    </div>
                  </section>
                ))}

                {data.type === 'username' && counts.confirmed > 0 && (
                  <p className="disclaimer">Cùng username trên nhiều trang không chắc chắn là cùng một người.</p>
                )}
              </>
            )}

            <div className="result-actions">
              <button className="btn-secondary" onClick={reset}>Truy vết mới</button>
              <button className="btn-secondary" onClick={exportJson}>Xuất JSON</button>
              <button className="btn-secondary" onClick={exportCsv}>Xuất CSV</button>
            </div>
          </>
        )}
      </main>

      <footer className="footer">
        <span className="version">OmniTrace v2.0</span>
        <span className="version">Chỉ dùng cho mục đích hợp pháp</span>
      </footer>
    </div>
  )
}

export default App
