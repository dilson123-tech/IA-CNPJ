import { clearToken } from '../../services/auth';

type HeaderProps = {
  title: string;
};

export default function Header({ title }: HeaderProps) {
  function handleLogout() {
    clearToken();

    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  return (
    <header className="app-header">
      <div>
        <p className="app-header-eyebrow">IA-CNPJ Engine</p>
        <h1 className="app-header-title">{title}</h1>
      </div>

      <button className="app-header-logout" type="button" onClick={handleLogout}>
        Sair
      </button>
    </header>
  );
}
