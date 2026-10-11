import { Login } from './pages/Auth/Login';
import { SignUp } from './pages/Auth/SignUp'
import { Route,Routes } from 'react-router-dom';
import './App.css';
import { Home } from './pages/Home/Home';
import { Menu } from './pages/menu/Menu';
import { Cart } from './pages/Cart/Cart';
import { Orders } from './pages/Orders/Orders';
import { Admin } from './pages/Admin/Admin';
import { AdminMenuPage } from './pages/Admin/AdminMenuPage';
import { AdminAnalytics } from './pages/Admin/AdminAnalytics';


function App() {

  return (
    <>
      <Routes>
        <Route path='/login' element={<Login />} />
        <Route path='/signup' element={<SignUp />} />
        <Route path='/home' element={<Home />} />
        <Route path='/canteen/:canteenId' element={<Menu />} />
        <Route path='/cart/:canteenId' element={<Cart />} />
        <Route path='/orders' element={<Orders />} />
        <Route path='/admin' element={<Admin />} />
        <Route path='/admin/menu' element={<AdminMenuPage />} />
        <Route path='/admin/analytics' element={<AdminAnalytics />} />
      </Routes>
     
    </>
  )
}

export default App;
