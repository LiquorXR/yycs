import { Link } from 'react-router-dom'
import PrivacyContent from '@/components/PrivacyContent'

export default function PrivacyPage() {
  return (
    <main className="fx-paper fx-cloud min-h-screen page-enter">
      <header className="sticky top-0 z-10 border-b border-gold/15 bg-[#3a0a0a]/92 backdrop-blur-md">
        <div className="flex h-[48px] items-center justify-between px-4">
          <Link
            to="/calc"
            aria-label="返回测算页"
            className="grid size-8 place-items-center rounded-full text-muted transition-colors hover:bg-white/8 hover:text-gold"
          >
            <svg viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </Link>
          <div className="font-kai text-[15px] font-bold tracking-[0.2em] text-gold-light">
            隐私政策
          </div>
          <span className="w-8" aria-hidden="true" />
        </div>
      </header>

      <div className="mx-auto max-w-[640px] p-4 pb-2">
        <div className="rounded-[16px] border border-border-gold bg-surface-card p-4 shadow-card">
          <PrivacyContent />
        </div>
      </div>
    </main>
  )
}
