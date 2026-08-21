import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import PageTransition from './PageTransition'

export default function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [pathname])

  return (
    <PageTransition>
      <Outlet />
    </PageTransition>
  )
}