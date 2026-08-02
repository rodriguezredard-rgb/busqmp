import { useEffect, useState } from 'react';
import CategoryPicker from './CategoryPicker';
import KeywordTagInput from './KeywordTagInput';
import Landing from './Landing';
import { recoverySession, refreshSession, signOut, storedSession, updateCredentials } from './auth';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const emptyProfile = {
  name: '', industry: '', include_keywords: [], exclude_keywords: [],
  selected_categories: [],
  opportunity_type: 'licitacion', region: '', organization: '', status: '',
  minimum_amount: null, maximum_amount: null, recipient_email: '',
  delivery_time: '09:00', timezone: 'America/Santiago', enabled: true,
};

function displayDate(value) {
  return value ? new Date(value).toLocaleString('es-CL', {
    timeZone: 'America/Santiago', dateStyle: 'short', timeStyle: 'short',
  }) : 'No informada';
}

function displayAmount(item) {
  if (item.amount == null) return 'Monto no informado';
  try {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency', currency: item.currency || 'CLP', maximumFractionDigits: 0,
    }).format(item.amount);
  } catch {
    return `$ ${Number(item.amount).toLocaleString('es-CL')} ${item.currency || 'CLP'}`;
  }
}

function Dashboard({ session, onSessionChange }) {
  const [activeModule, setActiveModule] = useState('settings');
  const [settingsPage, setSettingsPage] = useState(session.recovery ? 'account' : 'profiles');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [marketType, setMarketType] = useState('licitacion');
  const [theme, setTheme] = useState(() => localStorage.getItem('busqmp_theme') || 'system');
  const [items, setItems] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [categorySearch, setCategorySearch] = useState('');
  const [form, setForm] = useState(emptyProfile);
  const [editingId, setEditingId] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [searchProfileId, setSearchProfileId] = useState('manual');
  const [searchFilters, setSearchFilters] = useState({ region: '', organization: '', status: '' });
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const pageSize = 20;
  const isAgile = activeModule === 'compra_agil';
  const isSettings = activeModule === 'settings';
  const isProfiles = isSettings && settingsPage === 'profiles';
  const authHeaders = { Authorization: `Bearer ${session.access_token}` };

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('busqmp_theme', theme);
  }, [theme]);

  async function loadProfiles() {
    const response = await fetch(`${API}/profiles`, { headers: authHeaders });
    if (!response.ok) throw new Error('No se pudieron cargar los perfiles');
    const data = await response.json();
    setProfiles(data);
    return data;
  }

  async function loadCategories() {
    const response = await fetch(`${API}/opportunities/categories?limit=5000`);
    if (!response.ok) throw new Error('No se pudieron cargar los rubros');
    setCategories(await response.json());
  }

  async function search(event, requestedPage = 0, requestedModule = activeModule) {
    event?.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams({
        keyword,
        opportunity_type: requestedModule,
        limit: String(pageSize),
        offset: String(requestedPage * pageSize),
      });
      Object.entries(searchFilters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const response = await fetch(`${API}/opportunities?${params}`);
      if (!response.ok) throw new Error('No se pudo realizar la búsqueda');
      setItems(await response.json());
      setTotal(Number(response.headers.get('X-Total-Count') || 0));
      setPage(requestedPage);
      setMessage('');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function switchModule(module) {
    setActiveModule(module);
    if (module === 'settings') {
      setSettingsPage('menu');
      setMessage('');
      return;
    }
    setMarketType(module);
    setItems([]); setTotal(0); setPage(0);
    try {
      const availableProfiles = profiles.length ? profiles : await loadProfiles();
      const selected = availableProfiles.find((profile) => String(profile.id) === String(searchProfileId)
        && profile.opportunity_type === module);
      const fallback = availableProfiles.find((profile) => profile.opportunity_type === module);
      if (selected || fallback) await searchSavedProfile(selected || fallback, module, 0);
      else { setSearchProfileId('manual'); await search(null, 0, module); }
    } catch (error) { setMessage(error.message); }
  }

  async function searchSavedProfile(profile, module = activeModule, requestedPage = 0) {
    setLoading(true); setSearchProfileId(String(profile.id));
    try {
      const params = new URLSearchParams({ opportunity_type: module, limit: String(pageSize), offset: String(requestedPage * pageSize) });
      const response = await fetch(`${API}/profiles/${profile.id}/matches?${params}`, { headers: authHeaders });
      if (!response.ok) throw new Error('No se pudo aplicar la búsqueda guardada');
      setItems(await response.json());
      setTotal(Number(response.headers.get('X-Total-Count') || 0));
      setPage(requestedPage); setMessage('');
    } catch (error) { setMessage(error.message); } finally { setLoading(false); }
  }

  function chooseSearchProfile(value) {
    setSearchProfileId(value); setPage(0);
    if (value === 'manual') { setItems([]); setTotal(0); return; }
    const profile = profiles.find((item) => String(item.id) === value);
    if (profile) searchSavedProfile(profile, activeModule, 0);
  }

  function changeResultsPage(nextPage) {
    const profile = profiles.find((item) => String(item.id) === searchProfileId);
    return profile ? searchSavedProfile(profile, activeModule, nextPage) : search(null, nextPage);
  }

  useEffect(() => {
    if (!session.recovery) openSettings('profiles');
  }, []);

  async function saveProfile(event) {
    event.preventDefault();
    setLoading(true);
    const method = editingId ? 'PUT' : 'POST';
    const url = editingId ? `${API}/profiles/${editingId}` : `${API}/profiles`;
    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(form),
      });
      if (!response.ok) throw new Error('Revisa el correo y los datos ingresados');
      setMessage('Configuración guardada correctamente.');
      setForm(emptyProfile);
      setEditingId(null);
      await loadProfiles();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  function edit(profile) {
    setEditingId(profile.id);
    setForm({ ...profile });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function remove(id) {
    if (!window.confirm('¿Eliminar este perfil de búsqueda?')) return;
    await fetch(`${API}/profiles/${id}`, { method: 'DELETE', headers: authHeaders });
    await loadProfiles();
  }

  const set = (field, value) => setForm((old) => ({ ...old, [field]: value }));
  const setSearch = (field, value) => setSearchFilters((old) => ({ ...old, [field]: value }));
  const toggleCategory = (code) => set('selected_categories', form.selected_categories.includes(code)
    ? form.selected_categories.filter((item) => item !== code)
    : [...form.selected_categories, code]);

  async function openSettings(pageName) {
    setActiveModule('settings');
    setSettingsPage(pageName); setMessage('');
    if (pageName === 'profiles') {
      const requests = [loadProfiles()];
      if (!categories.length) requests.push(loadCategories());
      Promise.all(requests).catch((error) => setMessage(error.message));
    }
  }

  async function changeCredentials(event) {
    event.preventDefault(); setLoading(true); setMessage('');
    const data = new FormData(event.currentTarget);
    const values = {};
    if (data.get('email')) values.email = data.get('email');
    if (data.get('password')) values.password = data.get('password');
    try { await updateCredentials(session.access_token, values); setMessage(session.recovery ? 'Contraseña actualizada correctamente. Ya puedes usar tu cuenta.' : 'Credenciales actualizadas. Revisa tu correo si cambiaste el email.'); event.currentTarget.reset(); }
    catch (error) { setMessage(error.message); } finally { setLoading(false); }
  }

  async function logout() { await signOut(session.access_token); onSessionChange(null); }

  return <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
    <aside className="sidebar" onClick={(event) => { if (sidebarCollapsed && !event.target.closest('button')) setSidebarCollapsed(false); }}>
      <div className="brand"><span>BO</span><div><strong>Oportunidades</strong><small>Mercado Público</small></div><button className="sidebar-toggle" aria-label={sidebarCollapsed ? 'Mostrar menú' : 'Ocultar menú'} onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>{sidebarCollapsed ? '›' : '‹'}</button></div>
      <small className="nav-caption">Principal</small>
      <nav className="module-nav" aria-label="Módulos de oportunidades">
        <button className={`primary-nav ${isProfiles ? 'active' : ''}`} onClick={() => openSettings('profiles')}><span>＋</span><div><strong>Configurar búsquedas</strong><small>Recibe oportunidades por correo</small></div></button>
        <small className="nav-caption inline-caption">Explorar oportunidades</small>
        <button className={`market-parent ${activeModule === 'licitacion' || activeModule === 'compra_agil' ? 'active' : ''}`} onClick={() => switchModule(marketType)}><span>MP</span><div><strong>Mercado Público</strong><small>Licitaciones y compras ágiles</small></div><b>›</b></button>
        <button className={activeModule === 'settings' && !isProfiles ? 'active' : ''} onClick={() => switchModule('settings')}><span>⚙</span><div><strong>Settings</strong><small>Cuenta y preferencias</small></div></button>
      </nav>
      <div className="sidebar-note"><span className="live-dot" aria-hidden="true" />Sincronización automática activa</div>
      <button className="sidebar-account" onClick={() => switchModule('settings')}><span>{session.user?.email?.slice(0, 1).toUpperCase() || 'U'}</span><div><strong>{session.user?.email || 'Mi cuenta'}</strong><small>Administrar cuenta</small></div></button>
    </aside>

    <main className="app">
      <header className="page-header"><div><small className="eyebrow">{isSettings ? 'Configuración' : 'Módulo'}</small><h1>{isSettings ? settingsPage === 'profiles' ? 'Búsquedas programadas' : settingsPage === 'appearance' ? 'Apariencia' : settingsPage === 'account' ? 'Credenciales de acceso' : 'Settings' : isAgile ? 'Compras Ágiles' : 'Licitaciones'}</h1><p>{isSettings ? 'Administra tus búsquedas, apariencia y cuenta.' : isAgile ? 'Explora oportunidades de compra rápida.' : 'Encuentra procesos activos para ofertar.'}</p></div>{!isSettings && <span className="result-count"><strong>{total.toLocaleString('es-CL')}</strong> resultados</span>}</header>
      {message && <div className="notice" onClick={() => setMessage('')}>{message}</div>}

      {!isSettings && <>
      <section className="panel module-panel"><div className="section-heading"><div><h2>Buscar {isAgile ? 'compras ágiles' : 'licitaciones'}</h2><p>Filtra los registros guardados en la base de oportunidades.</p></div><span className="module-chip">{isAgile ? 'Compra Ágil' : 'Licitación'}</span></div>
        <div className="saved-search-selector"><label>Tipo de compra<select value={activeModule} onChange={(event) => switchModule(event.target.value)}><option value="licitacion">Licitaciones</option><option value="compra_agil">Compras Ágiles</option></select></label><label>Búsqueda aplicada<select value={searchProfileId} onChange={(event) => chooseSearchProfile(event.target.value)}><option value="manual">Búsqueda nueva en {isAgile ? 'Compras Ágiles' : 'Licitaciones'}</option>{profiles.filter((profile) => profile.opportunity_type === activeModule).map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></label>{searchProfileId !== 'manual' && <div className="applied-profile"><span>Filtros configurados</span>{(() => { const profile = profiles.find((item) => String(item.id) === searchProfileId); return profile ? <><b>{profile.name}</b><small>{[...profile.include_keywords, ...profile.selected_categories.map((code) => `Rubro ${code}`), profile.region, profile.organization].filter(Boolean).slice(0, 6).join(' · ') || 'Todos los registros'}</small></> : null; })()}</div>}</div>
        {searchProfileId === 'manual' && <form className="search-filters" onSubmit={(event) => search(event, 0)}>
          <label className="wide">Palabra clave<input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Ej. servicio, mantención, equipos" /></label>
          <label>Región<input value={searchFilters.region} onChange={(e) => setSearch('region', e.target.value)} /></label>
          <label>Organismo<input value={searchFilters.organization} onChange={(e) => setSearch('organization', e.target.value)} /></label>
          <label>Estado<input value={searchFilters.status} onChange={(e) => setSearch('status', e.target.value)} /></label>
          <div className="actions"><button disabled={loading}>{loading ? 'Buscando…' : `Buscar ${isAgile ? 'compras ágiles' : 'licitaciones'}`}</button></div>
        </form>}
        <div className="result-summary"><strong>{total.toLocaleString('es-CL')} resultados</strong>{total > 0 && <span>Página {page + 1} de {Math.ceil(total / pageSize)}</span>}</div>
        <div className="results">{items.map((item) => <article className="result-card" key={item.id}>
          <div className="result-card-head"><div className="result-labels"><span className="result-type">{item.opportunity_type === 'compra_agil' ? 'Compra Ágil' : 'Licitación'}</span><span className="result-code">{item.external_id}</span></div><span className="status-pill">{item.status || 'Sin estado'}</span></div>
          <h3 className="result-title">{item.title}</h3>
          <p className="result-organization"><span>{item.organization || 'Organismo no informado'}</span><span>{item.region || 'Región no informada'}</span></p>
          <div className="result-metadata"><span><small>Publicación</small>{displayDate(item.publish_date)}</span><span><small>Cierre</small>{displayDate(item.closing_date)}</span><span className="amount"><small>{item.opportunity_type === 'compra_agil' ? 'Monto disponible' : 'Monto estimado'}</small>{displayAmount(item)}</span></div>
          {item.url && <a className="result-link" href={item.url} target="_blank" rel="noreferrer">Ver oportunidad <span aria-hidden="true">↗</span></a>}
        </article>)}</div>
        {!loading && !items.length && <div className="empty-state">No hay resultados para los filtros seleccionados.</div>}
        {total > pageSize && <nav className="pagination" aria-label="Paginación"><button className="secondary" disabled={loading || page === 0} onClick={() => changeResultsPage(page - 1)}>Anterior</button><button disabled={loading || (page + 1) * pageSize >= total} onClick={() => changeResultsPage(page + 1)}>Siguiente</button></nav>}
      </section>
      </>}

      {isSettings && settingsPage === 'menu' && <section className="settings-layer panel"><div className="settings-user"><span>{session.user?.email?.slice(0, 1).toUpperCase()}</span><div><strong>{session.user?.email}</strong><small>Cuenta activa</small></div></div><h2>Configurar</h2><div className="settings-menu"><button onClick={() => openSettings('profiles')}><span>⌕</span><div><strong>Búsquedas programadas</strong><small>Palabras, rubros y alertas por correo</small></div><b>›</b></button><button onClick={() => openSettings('appearance')}><span>◐</span><div><strong>Apariencia</strong><small>Modo claro, oscuro o del sistema</small></div><b>›</b></button><button onClick={() => openSettings('account')}><span>♙</span><div><strong>Credenciales de acceso</strong><small>Correo electrónico y contraseña</small></div><b>›</b></button></div><button className="logout-button" onClick={logout}>Cerrar sesión</button></section>}

      {isSettings && settingsPage !== 'menu' && <button className="settings-back" onClick={() => setSettingsPage('menu')}>← Volver a Settings</button>}

      {isSettings && settingsPage === 'appearance' && <section className="panel appearance-panel"><h2>Skin de la plataforma</h2><p className="panel-intro">Elige cómo quieres ver la interfaz en este dispositivo.</p><div className="theme-options">{[['light','Claro','Interfaz luminosa y limpia'],['dark','Oscuro','Menos brillo y mayor contraste'],['system','Sistema','Sigue la configuración del equipo']].map(([value,label,description]) => <button className={theme === value ? 'selected' : ''} key={value} onClick={() => setTheme(value)}><i className={`theme-preview ${value}`} /><span><strong>{label}</strong><small>{description}</small></span><b>{theme === value ? '✓' : ''}</b></button>)}</div></section>}

      {isSettings && settingsPage === 'account' && <section className="panel account-panel"><h2>Credenciales de acceso</h2><p className="panel-intro">Actualiza el correo o define una nueva contraseña para tu cuenta.</p><form className="account-form" onSubmit={changeCredentials}><label>Nuevo correo electrónico<input type="email" name="email" placeholder={session.user?.email} /></label><label>Nueva contraseña<input type="password" name="password" minLength="6" autoComplete="new-password" placeholder="Mínimo 6 caracteres" /></label><div className="actions"><button disabled={loading}>Guardar cambios</button></div></form><div className="session-section"><div><strong>Sesión actual</strong><small>{session.user?.email || 'Cuenta autenticada'}</small></div><button className="session-logout" onClick={logout}>Cerrar sesión</button></div></section>}

      {isProfiles && <>
      <section className="panel">
        <h2>{editingId ? 'Editar búsqueda programada' : 'Nueva búsqueda programada'}</h2>
        <p className="panel-intro">Guarda un rubro y define qué palabras deben aparecer y cuáles deben descartarse.</p>
        <form onSubmit={saveProfile} className="grid">
          <label>Nombre de la búsqueda<input required value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Ej. Servicios eléctricos" /></label>
          <label className="wide">Palabras que debe buscar<KeywordTagInput key={`${editingId ?? 'new'}-include`} value={form.include_keywords} onChange={(value) => set('include_keywords', value)} placeholder="Ej. vet*, cableado, mantención" /><small>Presiona coma o Enter para agregar cada tag. Usa * para incluir variantes: vet* encuentra veterinaria y veterinarios.</small></label>
          <label className="wide">Palabras que debe excluir<KeywordTagInput key={`${editingId ?? 'new'}-exclude`} value={form.exclude_keywords} onChange={(value) => set('exclude_keywords', value)} placeholder="Ej. arriend*, usado" tone="exclude" /><small>Estas palabras y sus variantes no aparecerán en los resultados enviados.</small></label>
          <CategoryPicker categories={categories} selected={form.selected_categories} search={categorySearch} onSearch={setCategorySearch} toggle={toggleCategory} />
          <label>Tipo de compra<select value={form.opportunity_type} onChange={(e) => set('opportunity_type', e.target.value)}>{form.opportunity_type === 'all' && <option value="all" disabled>Ambos (configuración anterior)</option>}<option value="licitacion">Licitación</option><option value="compra_agil">Compra Ágil</option></select></label>
          <label>Región<input value={form.region} onChange={(e) => set('region', e.target.value)} /></label>
          <label>Organismo<input value={form.organization} onChange={(e) => set('organization', e.target.value)} /></label>
          <label>Estado<input value={form.status} onChange={(e) => set('status', e.target.value)} /></label>
          <label>Monto mínimo<input type="number" value={form.minimum_amount ?? ''} onChange={(e) => set('minimum_amount', e.target.value ? Number(e.target.value) : null)} /></label>
          <label>Monto máximo<input type="number" value={form.maximum_amount ?? ''} onChange={(e) => set('maximum_amount', e.target.value ? Number(e.target.value) : null)} /></label>
          <label>Correo destinatario<input required type="email" value={form.recipient_email} onChange={(e) => set('recipient_email', e.target.value)} /></label>
          <label>Hora diaria<input required type="time" value={form.delivery_time} onChange={(e) => set('delivery_time', e.target.value)} /></label>
          <label className="check"><input type="checkbox" checked={form.enabled} onChange={(e) => set('enabled', e.target.checked)} /> Envío diario activo</label>
          <div className="actions"><button disabled={loading}>{editingId ? 'Guardar cambios' : 'Crear búsqueda'}</button>{editingId && <button type="button" className="secondary" onClick={() => { setEditingId(null); setForm(emptyProfile); }}>Cancelar</button>}</div>
        </form>
      </section>

      <section className="panel"><h2>Mis búsquedas programadas</h2><div className="profiles">
        {profiles.map((profile) => <article key={profile.id}><div><strong>{profile.name}</strong><p><span className="profile-industry">{profile.opportunity_type === 'compra_agil' ? 'Compra Ágil' : profile.opportunity_type === 'licitacion' ? 'Licitación' : 'Ambos (anterior)'}</span> · {profile.delivery_time} · {profile.recipient_email}</p><small><b>Incluye:</b> {profile.include_keywords.join(', ') || 'Todas'} · <b>Excluye:</b> {profile.exclude_keywords.join(', ') || 'Ninguna'} · <b>Rubros:</b> {profile.selected_categories?.length || 0} · {profile.enabled ? 'Activa' : 'Pausada'}</small></div><div><button onClick={() => edit(profile)}>Editar</button><button className="danger" onClick={() => remove(profile.id)}>Eliminar</button></div></article>)}
        {!profiles.length && <p>Aún no tienes búsquedas programadas.</p>}
      </div></section>
      </>}
    </main>
  </div>;
}

export default function App() {
  const [session, setSession] = useState(() => recoverySession() || storedSession());

  useEffect(() => {
    if (!session?.refresh_token) return;
    const expiresSoon = !session.expires_at || session.expires_at * 1000 < Date.now() + 60000;
    if (expiresSoon) refreshSession(session.refresh_token).then(setSession).catch(() => setSession(null));
  }, []);

  return session?.access_token ? <Dashboard session={session} onSessionChange={setSession} /> : <Landing onAuthenticated={setSession} />;
}
