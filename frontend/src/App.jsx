import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const EXAMPLE_QUESTIONS = [
  "What breast cancer trials are near Newark, Delaware?",
  "What is triple negative breast cancer?",
  "Are there immunotherapy trials for lung cancer in Delaware?",
  "What are the cancer mortality rates in Delaware?",
  "What clinical trials is Helen F. Graham Cancer Center running?",
]

function SourceBadge({ source }) {
  const colors = {
    trial: { bg: 'rgba(34,211,238,0.1)', border: 'rgba(34,211,238,0.3)', text: '#22d3ee' },
    pubmed: { bg: 'rgba(167,139,250,0.1)', border: 'rgba(167,139,250,0.3)', text: '#a78bfa' },
    fda: { bg: 'rgba(251,146,60,0.1)', border: 'rgba(251,146,60,0.3)', text: '#fb923c' },
    other: { bg: 'rgba(148,163,184,0.1)', border: 'rgba(148,163,184,0.3)', text: '#94a3b8' },
  }
  const c = colors[source.type] || colors.other
  const label = source.type === 'trial' ? `NCT: ${source.id}` : source.type === 'pubmed' ? `PubMed: ${source.id}` : source.type
  
  return (
    <span style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text, padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", whiteSpace: 'nowrap' }}>
      {label}
    </span>
  )
}

function Message({ msg, isLast }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end mb-6 animate-fade-up">
        <div style={{ background: 'var(--accent-dim)', borderRadius: '16px 16px 4px 16px', padding: '12px 18px', maxWidth: '75%', fontSize: '15px', lineHeight: '1.6' }}>
          {msg.text}
        </div>
      </div>
    )
  }
  
  return (
    <div className="mb-6 animate-fade-up">
      <div className="flex items-start gap-3">
        <div style={{ width: '32px', height: '32px', borderRadius: '10px', background: 'linear-gradient(135deg, var(--accent-dim), var(--accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0 }}>
          TS
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: '4px 16px 16px 16px', padding: '16px 20px', border: '1px solid var(--border)', fontSize: '15px', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>
            {msg.text}
          </div>
          {msg.sources && msg.sources.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 ml-1">
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginRight: '4px', lineHeight: '24px' }}>Sources:</span>
              {msg.sources.map((s, i) => <SourceBadge key={i} source={s} />)}
            </div>
          )}
          {msg.time && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', marginLeft: '4px', fontFamily: "'JetBrains Mono', monospace" }}>
              {msg.time}s
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 mb-6 animate-fade-up">
      <div style={{ width: '32px', height: '32px', borderRadius: '10px', background: 'linear-gradient(135deg, var(--accent-dim), var(--accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', flexShrink: 0 }}>
        TS
      </div>
      <div style={{ background: 'var(--bg-card)', borderRadius: '4px 16px 16px 16px', padding: '16px 20px', border: '1px solid var(--border)', display: 'flex', gap: '6px', alignItems: 'center' }}>
        <div className="typing-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)' }}></div>
        <div className="typing-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)' }}></div>
        <div className="typing-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)' }}></div>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '8px' }}>Searching 12,761 documents...</span>
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => { inputRef.current?.focus() }, [])

  const sendMessage = async (text) => {
    const question = text || input.trim()
    if (!question || loading) return
    
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: question }])
    setLoading(true)
    
    try {
      const res = await axios.post('/ask', { question })
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: res.data.answer,
        sources: res.data.sources,
        time: res.data.time,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Sorry, I encountered an error. Make sure the backend is running on port 8000.',
      }])
    }
    
    setLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header style={{ borderBottom: '1px solid var(--border)', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-3">
          <div className="animate-glow" style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'linear-gradient(135deg, var(--accent-dim), var(--accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '15px' }}>
            TS
          </div>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 600, letterSpacing: '-0.02em' }}>TrialScope Delaware</h1>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Clinical Trial Navigator for Cancer Patients</p>
          </div>
        </div>
        <div className="flex items-center gap-2" style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e', display: 'inline-block' }}></span>
          12,761 documents indexed
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin" style={{ padding: '24px' }}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full" style={{ maxWidth: '600px', margin: '0 auto' }}>
            <div className="animate-glow" style={{ width: '64px', height: '64px', borderRadius: '20px', background: 'linear-gradient(135deg, var(--accent-dim), var(--accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '22px', marginBottom: '24px' }}>
              TS
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '8px', letterSpacing: '-0.02em' }}>Welcome to TrialScope</h2>
            <p style={{ fontSize: '15px', color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '32px', lineHeight: '1.6' }}>
              Ask me about cancer clinical trials in Delaware, treatment options, screening programs, and cancer statistics. I search across 10,980 trials and 937 research articles.
            </p>
            <div className="w-full space-y-2">
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Try asking</p>
              {EXAMPLE_QUESTIONS.map((q, i) => (
                <button key={i} onClick={() => sendMessage(q)}
                  style={{ display: 'block', width: '100%', textAlign: 'left', padding: '12px 16px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '10px', color: 'var(--text-secondary)', fontSize: '14px', cursor: 'pointer', transition: 'all 0.2s' }}
                  onMouseOver={e => { e.target.style.borderColor = 'var(--accent-dim)'; e.target.style.color = 'var(--text-primary)' }}
                  onMouseOut={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text-secondary)' }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            {messages.map((msg, i) => <Message key={i} msg={msg} isLast={i === messages.length - 1} />)}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ borderTop: '1px solid var(--border)', padding: '16px 24px', background: 'var(--bg-secondary)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="Ask about Delaware cancer trials..."
            disabled={loading}
            style={{ flex: 1, padding: '14px 18px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '12px', color: 'var(--text-primary)', fontSize: '15px', outline: 'none', transition: 'border-color 0.2s', fontFamily: "'DM Sans', sans-serif" }}
            onFocus={e => e.target.style.borderColor = 'var(--accent-dim)'}
            onBlur={e => e.target.style.borderColor = 'var(--border)'}
          />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()}
            style={{ padding: '14px 24px', background: loading || !input.trim() ? 'var(--border)' : 'var(--accent-dim)', color: loading || !input.trim() ? 'var(--text-muted)' : 'white', border: 'none', borderRadius: '12px', fontWeight: 600, fontSize: '14px', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer', transition: 'all 0.2s', fontFamily: "'DM Sans', sans-serif" }}>
            {loading ? '...' : 'Ask'}
          </button>
        </div>
        <p style={{ textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
          Powered by FAISS + Groq Llama 3.3 70B | Data from ClinicalTrials.gov, PubMed, FDA
        </p>
      </div>
    </div>
  )
}
