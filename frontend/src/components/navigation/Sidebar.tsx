import { Link } from 'react-router-dom'

export function Sidebar() {
  return (
    <aside>
      <ul>
        <li>
          <Link to="/dashboard/merchant">Dashboard</Link>
        </li>
      </ul>
    </aside>
  )
}
