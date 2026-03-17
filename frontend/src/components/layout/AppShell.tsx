import type { ReactNode } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

type AppShellProps = {
  title: string;
  children: ReactNode;
};

export default function AppShell({ title, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-shell-content">
        <Header title={title} />
        <main className="app-shell-main">{children}</main>
      </div>
    </div>
  );
}
