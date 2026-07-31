import { useEffect, useState } from 'react';
import CategoryPicker from './CategoryPicker';
import KeywordTagInput from './KeywordTagInput';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const emptyProfile = {
  name: '', industry: '', include_keywords: [], exclude_keywords: [],
  selected_categories: [],
  opportunity_type: 'all', region: '', organization: '', status: '',
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

export default function App() {
  const [activeModule, setActiveModule] = useState('licitacion');
  const [items, setItems] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [categorySearch, setCategorySearch] = useState('');
  const [form, setForm] = useState(emptyProfile);
  const [editingId, setEditingId] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [searchFilters, setSearchFilters] = useState({ region: '', organization: '', status: '' });
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const pageSize = 20;
  const isAgile = activeModule === 'compra_agil';
  const isProfiles = activeModule === 'profiles';

  async function loadProfiles() {
    const response = await fetch(`${API}/profiles`);
    if (!response.ok) throw new Error('No se pudieron cargar los perfiles');
    setProfiles(await response.json());
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

  function switchModule(module) {
    setActiveModule(module);
    if (module === 'profiles') {
      setMessage('');
      const requests = [loadProfiles()];
      if (!categories.length) requests.push(loadCategories());
      Promise.all(requests).catch((error) => setMessage(error.message));
      return;
    }
    setItems([]);
    setTotal(0);
    setPage(0);
    search(null, 0, module);
  }

  useEffect(() => {
    search(null, 0, 'licitacion').catch((error) => setMessage(error.message));
  }, []);

  async function saveProfile(event) {
    event.preventDefault();
    setLoading(true);
    const method = editingId ? 'PUT' : 'POST';
    const url = editingId ? `${API}/profiles/${editingId}` : `${API}/profiles`;
    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
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
    await fetch(`${API}/profiles/${id}`, { method: 'DELETE' });
    await loadProfiles();
  }

  const set = (field, value) => setForm((old) => ({ ...old, [field]: value }));
  const setSearch = (field, value) => setSearchFilters((old) => ({ ...old, [field]: value }));
  const toggleCategory = (code) => set('selected_categories', form.selected_categories.includes(code)
    ? form.selected_categories.filter((item) => item !== code)
    : [...form.selected_categories, code]);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span>BO</span><div><strong>Oportunidades</strong><small>Mercado Público</small></div></div>
      <nav className="module-nav" aria-label="Módulos de oportunidades">
        <button className={activeModule === 'licitacion' ? 'active' : ''} onClick={() => switchModule('licitacion')}><span>L</span><div><strong>Licitaciones</strong><small>Procesos activos</small></div></button>
        <button className={activeModule === 'compra_agil' ? 'active' : ''} onClick={() => switchModule('compra_agil')}><span>CA</span><div><strong>Compras Ágiles</strong><small>Oportunidades rápidas</small></div></button>
        <button className={activeModule === 'profiles' ? 'active' : ''} onClick={() => switchModule('profiles')}><span>R</span><div><strong>Rubros guardados</strong><small>Palabras y exclusiones</small></div></button>
      </nav>
      <div className="sidebar-note">Datos sincronizados automáticamente desde Mercado Público.</div>
    </aside>

    <main className="app">
      <header><div><small className="eyebrow">Módulo</small><h1>{isProfiles ? 'Rubros guardados' : isAgile ? 'Compras Ágiles' : 'Licitaciones'}</h1><p>{isProfiles ? 'Configura palabras clave, exclusiones y alertas diarias.' : isAgile ? 'Explora oportunidades de compra rápida.' : 'Encuentra procesos activos para ofertar.'}</p></div>{!isProfiles && <span>{total.toLocaleString('es-CL')} resultados</span>}</header>
      {message && <div className="notice" onClick={() => setMessage('')}>{message}</div>}

      {!isProfiles && <>
      <section className="panel module-panel"><div className="section-heading"><div><h2>Buscar {isAgile ? 'compras ágiles' : 'licitaciones'}</h2><p>Filtra los registros guardados en la base de oportunidades.</p></div><span className="module-chip">{isAgile ? 'Compra Ágil' : 'Licitación'}</span></div>
        <form className="search-filters" onSubmit={(event) => search(event, 0)}>
          <label className="wide">Palabra clave<input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Ej. servicio, mantención, equipos" /></label>
          <label>Región<input value={searchFilters.region} onChange={(e) => setSearch('region', e.target.value)} /></label>
          <label>Organismo<input value={searchFilters.organization} onChange={(e) => setSearch('organization', e.target.value)} /></label>
          <label>Estado<input value={searchFilters.status} onChange={(e) => setSearch('status', e.target.value)} /></label>
          <div className="actions"><button disabled={loading}>{loading ? 'Buscando…' : `Buscar ${isAgile ? 'compras ágiles' : 'licitaciones'}`}</button></div>
        </form>
        <div className="result-summary"><strong>{total.toLocaleString('es-CL')} resultados</strong>{total > 0 && <span>Página {page + 1} de {Math.ceil(total / pageSize)}</span>}</div>
        <div className="results">{items.map((item) => <article key={item.id}><div className="result-type">{item.opportunity_type === 'compra_agil' ? 'Compra Ágil' : 'Licitación'}</div><strong>{item.title}</strong><p>{item.organization || 'Organismo no informado'} · {item.region || 'Región no informada'}</p><div className="result-metadata"><span><small>Publicación</small>{displayDate(item.publish_date)}</span><span><small>Cierre</small>{displayDate(item.closing_date)}</span><span><small>{item.opportunity_type === 'compra_agil' ? 'Monto disponible' : 'Monto estimado'}</small>{displayAmount(item)}</span></div><small>{item.status || 'Sin estado'}</small>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Ver oportunidad</a>}</article>)}</div>
        {!loading && !items.length && <div className="empty-state">No hay resultados para los filtros seleccionados.</div>}
        {total > pageSize && <nav className="pagination" aria-label="Paginación"><button className="secondary" disabled={loading || page === 0} onClick={() => search(null, page - 1)}>Anterior</button><button disabled={loading || (page + 1) * pageSize >= total} onClick={() => search(null, page + 1)}>Siguiente</button></nav>}
      </section>
      </>}

      {isProfiles && <>
      <section className="panel">
        <h2>{editingId ? 'Editar búsqueda programada' : 'Nueva búsqueda programada'}</h2>
        <p className="panel-intro">Guarda un rubro y define qué palabras deben aparecer y cuáles deben descartarse.</p>
        <form onSubmit={saveProfile} className="grid">
          <label>Nombre del perfil<input required value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Ej. Servicios eléctricos" /></label>
          <label>Rubro<input required value={form.industry} onChange={(e) => set('industry', e.target.value)} placeholder="Ej. Electricidad industrial" /></label>
          <label className="wide">Palabras que debe buscar<KeywordTagInput key={`${editingId ?? 'new'}-include`} value={form.include_keywords} onChange={(value) => set('include_keywords', value)} placeholder="Ej. vet*, cableado, mantención" /><small>Presiona coma o Enter para agregar cada tag. Usa * para incluir variantes: vet* encuentra veterinaria y veterinarios.</small></label>
          <label className="wide">Palabras que debe excluir<KeywordTagInput key={`${editingId ?? 'new'}-exclude`} value={form.exclude_keywords} onChange={(value) => set('exclude_keywords', value)} placeholder="Ej. arriend*, usado" tone="exclude" /><small>Estas palabras y sus variantes no aparecerán en los resultados enviados.</small></label>
          <CategoryPicker categories={categories} selected={form.selected_categories} search={categorySearch} onSearch={setCategorySearch} toggle={toggleCategory} />
          <label>Tipo<select value={form.opportunity_type} onChange={(e) => set('opportunity_type', e.target.value)}><option value="all">Todas</option><option value="licitacion">Licitación</option><option value="compra_agil">Compra ágil</option></select></label>
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
        {profiles.map((profile) => <article key={profile.id}><div><strong>{profile.name}</strong><p><span className="profile-industry">{profile.industry}</span> · {profile.delivery_time} · {profile.recipient_email}</p><small><b>Incluye:</b> {profile.include_keywords.join(', ') || 'Todas'} · <b>Excluye:</b> {profile.exclude_keywords.join(', ') || 'Ninguna'} · <b>Rubros:</b> {profile.selected_categories?.length || 0} · {profile.enabled ? 'Activa' : 'Pausada'}</small></div><div><button onClick={() => edit(profile)}>Editar</button><button className="danger" onClick={() => remove(profile.id)}>Eliminar</button></div></article>)}
        {!profiles.length && <p>Aún no tienes búsquedas programadas.</p>}
      </div></section>
      </>}
    </main>
  </div>;
}
