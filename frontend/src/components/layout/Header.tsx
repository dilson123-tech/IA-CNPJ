type HeaderProps = {
  title: string;
};

export default function Header({ title }: HeaderProps) {
  return (
    <header className="app-header">
      <div>
        <p className="app-header-eyebrow">IA-CNPJ Engine</p>
        <h1 className="app-header-title">{title}</h1>
      </div>
    </header>
  );
}
