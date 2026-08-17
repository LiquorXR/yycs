import { createBrowserRouter } from 'react-router-dom'
import LandingPage from '../pages/LandingPage'
import CalcPage from '../pages/CalcPage'
import OrderPage from '../pages/OrderPage'
import PayPage from '../pages/PayPage'
import ReportPage from '../pages/ReportPage'
import ScrollToTop from '../components/ScrollToTop'

const router = createBrowserRouter([
  {
    element: <ScrollToTop />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/calc', element: <CalcPage /> },
      { path: '/order', element: <OrderPage /> },
      { path: '/pay/:orderNo', element: <PayPage /> },
      { path: '/report/:orderNo', element: <ReportPage /> },
    ],
  },
])

export default router
