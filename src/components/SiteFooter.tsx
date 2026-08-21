import { Link } from 'react-router-dom'
import { COMPANY_NAME, CONTACT_ADDRESS, ICP_NO } from '@/lib/agreement'

export default function SiteFooter() {
  return (
    <footer className="mt-8 border-t border-gold/10 bg-[#2e0808]/60 px-5 py-5 text-center backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] leading-relaxed text-muted">
        <span>© {new Date().getFullYear()} {COMPANY_NAME}</span>
        <span className="hidden sm:inline text-white/20">|</span>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noreferrer"
          className="hover:text-gold transition-colors underline decoration-white/15 underline-offset-2"
        >
          {ICP_NO}
        </a>
        <span className="hidden sm:inline text-white/20">|</span>
        <Link to="/privacy" className="text-gold hover:text-gold-light transition-colors underline decoration-gold/30 underline-offset-2">
          隐私政策
        </Link>
      </div>
      <p className="mt-1.5 text-[10px] leading-relaxed text-white/30">
        联系地址：{CONTACT_ADDRESS}
      </p>
      <p className="mt-1 text-[10px] leading-relaxed text-white/25">
        版权所有：{COMPANY_NAME}
      </p>
      <p className="mt-1 text-[10px] leading-relaxed text-white/25">
        生辰信息已加密存储，仅用于本次测算
      </p>
    </footer>
  )
}
