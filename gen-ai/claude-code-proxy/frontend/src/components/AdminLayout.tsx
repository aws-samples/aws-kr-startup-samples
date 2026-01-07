import { Link, NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/users', label: 'Users' },
  { to: '/models', label: 'Models' },
];

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition',
    isActive
      ? 'bg-surface-2 text-ink shadow-soft'
      : 'text-muted hover:text-ink hover:bg-surface-2',
  ].join(' ');

export default function AdminLayout() {
  return (
    <div className="min-h-screen">
      <div className="flex min-h-screen">
        <aside className="hidden w-56 flex-col border-r border-line bg-surface/85 backdrop-blur lg:flex">
          <div className="px-5 py-6">
            <Link to="/dashboard" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-sm font-semibold text-white shadow-soft">
                CP
              </div>
              <div>
                <div className="text-sm font-semibold text-ink">Claude Proxy</div>
                <div className="text-xs uppercase tracking-[0.32em] text-muted">Admin</div>
              </div>
            </Link>
          </div>
          <nav className="flex-1 px-3">
            <div className="px-2 pb-3 text-xs uppercase tracking-[0.3em] text-muted">Manage</div>
            <div className="space-y-1">
              {navItems.map((item) => (
                <NavLink key={item.to} to={item.to} className={navLinkClass}>
                  {item.label}
                </NavLink>
              ))}
            </div>
          </nav>
          <div className="px-5 py-6 text-xs text-muted">
            Token operations dashboard
          </div>
        </aside>

        <div className="flex-1">
          <div className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-surface/85 px-6 py-4 backdrop-blur lg:hidden">
            <Link to="/dashboard" className="text-sm font-semibold text-ink">
              Claude Proxy Admin
            </Link>
            <NavLink to="/users" className={navLinkClass}>
              Users
            </NavLink>
          </div>

          <div className="px-6 py-8 lg:px-10">
            <div className="mx-auto w-full max-w-6xl">
              <Outlet />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
