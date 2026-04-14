import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Dashboard',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
      </svg>
    ),
  },
  {
    to: '/search',
    label: 'Methodology Search',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path
          fillRule="evenodd"
          d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
          clipRule="evenodd"
        />
      </svg>
    ),
  },
  {
    to: '/assessment',
    label: 'Credit Assessment',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path
          fillRule="evenodd"
          d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
          clipRule="evenodd"
        />
      </svg>
    ),
  },
  {
    to: '/surveillance',
    label: 'Surveillance Alerts',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
    ),
  },
  {
    to: '/peer-comparison',
    label: 'Peer Comparison',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__brand-logo">
          <span className="sidebar__brand-mark">C</span>
        </div>
        <div className="sidebar__brand-text">
          <span className="sidebar__brand-name">CRISIL</span>
          <span className="sidebar__brand-subtitle">
            Rating Intelligence
          </span>
        </div>
      </div>

      <nav className="sidebar__nav">
        <ul className="sidebar__nav-list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to} className="sidebar__nav-item">
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `sidebar__nav-link ${isActive ? 'sidebar__nav-link--active' : ''}`
                }
              >
                <span className="sidebar__nav-icon">{item.icon}</span>
                <span className="sidebar__nav-label">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__footer-text">
          Rating Methodology<br />
          Intelligence System v1.0
        </div>
      </div>
    </aside>
  );
}
