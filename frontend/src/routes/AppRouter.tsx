import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { RegisterPage } from '../features/auth/pages/RegisterPage'
import { CustomerDashboardPage } from '../features/dashboard/pages/CustomerDashboardPage'
import { MerchantDashboardPage } from '../features/dashboard/pages/MerchantDashboardPage'
import { AdminDashboardPage } from '../features/dashboard/pages/AdminDashboardPage'
import { CartPage } from '../features/orders/pages/CartPage'
import { CheckoutPage } from '../features/orders/pages/CheckoutPage'
import { OrderDetailsPage } from '../features/orders/pages/OrderDetailsPage'
import { MyOrdersPage } from '../features/orders/pages/MyOrdersPage'
import { OrderConfirmationPage } from '../features/orders/pages/OrderConfirmationPage'
import { OrdersManagementPage } from '../features/orders/pages/OrdersManagementPage'
import { MerchantQrVerificationPage } from '../features/orders/pages/MerchantQrVerificationPage'
import { ProductManagementPage } from '../features/products/pages/ProductManagementPage'
import { StoreDetailsPage } from '../features/stores/pages/StoreDetailsPage'
import { StoreManagementPage } from '../features/stores/pages/StoreManagementPage'
import { StoresPage } from '../features/stores/pages/StoresPage'
import { AppLayout } from '../layouts/AppLayout'
import { DashboardLayout } from '../layouts/DashboardLayout'
import { NotFoundPage } from '../pages/NotFoundPage'
import { UnauthorizedPage } from '../pages/UnauthorizedPage'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicOnlyRoute } from './PublicOnlyRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route element={<ProtectedRoute allowedRoles={['CUSTOMER']} />}>
          <Route index element={<StoresPage />} />
          <Route path="stores/:storeId" element={<StoreDetailsPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="checkout" element={<CheckoutPage />} />
          <Route path="orders/:orderId" element={<OrderDetailsPage />} />
          <Route path="orders/:orderId/confirmation" element={<OrderConfirmationPage />} />
          <Route path="orders" element={<MyOrdersPage />} />
        </Route>
      </Route>

      <Route path="auth" element={<PublicOnlyRoute />}>
        <Route index element={<Navigate to="login" replace />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['CUSTOMER']} />}>
        <Route path="dashboard/customer" element={<CustomerDashboardPage />} />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['MERCHANT']} />}>
        <Route element={<DashboardLayout />}>
          <Route path="dashboard/merchant" element={<MerchantDashboardPage />} />
          <Route path="dashboard/merchant/orders" element={<OrdersManagementPage />} />
          <Route path="dashboard/merchant/verify" element={<MerchantQrVerificationPage />} />
          <Route path="dashboard/merchant/products" element={<ProductManagementPage />} />
          <Route path="dashboard/merchant/store" element={<StoreManagementPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
        <Route path="dashboard/admin" element={<AdminDashboardPage />} />
      </Route>

      <Route path="unauthorized" element={<UnauthorizedPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
