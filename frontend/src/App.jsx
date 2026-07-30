import { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const emptyProfile = {
  name: '', industry: '', include_keywords: [], exclude_keywords: [],
  opportunity_type: 'all', region: '', organization: '', status: '',
  minimum_amount: null, maximum_amount: null, recipient_email: '',
  delivery_time: '09:00', timezone: 'America/Santiago', enabled: true,
};

function words(value) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

export default function App() {
  const [items, setItems] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [form, setForm] = useState(emptyProfile);
  const [editingId, setEditingId] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [searchFilters, setSearchFilters] = useState({ opportunity_type: 'all', region: '', organization: '', status: '' });
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const pageSize = 20;

  async function loadProfiles() {
    const response = await fetch(`${API}/profiles`);
    if (!response.ok) throw new Error('No se pudieron cargar los perfiles');
    setProfiles(await response.json());
  }

  async function search(event, requestedPage = 0) {
    event?.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams({ keyword, limit: String(pageSize), offset: String(requestedPage * pageSize) });
      Object.entries(searchFilters).forEach(([key, value]) => {
        if (value && value !== 'all') params.set(key, value);
      });
      const response = await fetch(`${API}/opportunities?${params}`);
      if (!response.ok) throw new Error('No se pudo realizar la búsqueda');
      setItems(await response.json());
      setTotal(Number(response.headers.get('X-Total-Count') || 0));
      setPage(requestedPage);
      setMessage('');
    } catch (error) { setMessage(error.message); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    Promise.all([loadProfiles(), search()]).catch((error) => setMessage(error.message));
  }, []);

  async function saveProfile(event) {
    event.preventDefault();
    setLoading(true);
    const method = editingId ? 'PUT' : 'POST';
    const url = editingId ? `${API}/profiles/${editingId}` : `${API}/profiles`;
    try {
      const response = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
      });
      if (!response.ok) throw new Error('Revisa el correo y los datos ingresados');
      setMessage('Configuración guardada correctamente.');
      setForm(emptyProfile); setEditingId(null); await loadProfiles();
    } catch (error) { setMessage(error.message); }
    finally { setLoading(false); }
  }

  function edit(profile) {
    setEditingId(profile.id); setForm({ ...profile }); window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function remove(id) {
    if (!window.confirm('¿Eliminar este perfil de búsqueda?')) return;
    await fetch(`${API}/profiles/${id}`, { method: 'DELETE' });
    await loadProfiles();
  }

  const set = (field, value) => setForm((old) => ({ ...old, [field]: value }));

  return <main className="app">
    <header><div><h1>Buscador de oportunidades</h1><p>Configura tu rubro y recibe un resumen diario.</p></div><span>{total.toLocaleString('es-CL')} resultados</span></header>
    {message && <div className="notice" onClick={() => setMessage('')}>{message}</div>}

    <section className="panel">
      <h2>{editingId ? 'Editar búsqueda programada' : 'Nueva búsqueda programada'}</h2>
      <form onSubmit={saveProfile} className="grid">
        <label>Nombre del perfil<input required value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Ej. Servicios eléctricos" /></label>
        <label>Rubro<input required value={form.industry} onChange={(e) => set('industry', e.target.value)} placeholder="Ej. Electricidad industrial" /></label>
        <label className="wide">Palabras que debe buscar<input value={form.include_keywords.join(', ')} onChange={(e) => set('include_keywords', words(e.target.value))} placeholder="tableros eléctricos, cableado, mantención" /><small>Sepáralas con comas.</small></label>
        <label className="wide">Palabras que debe excluir<input value={form.exclude_keywords.join(', ')} onChange={(e) => set('exclude_keywords', words(e.target.value))} placeholder="arriendo, usado" /></label>
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
      {profiles.map((profile) => <article key={profile.id}><div><strong>{profile.name}</strong><p>{profile.industry} · {profile.delivery_time} · {profile.recipient_email}</p><small>{profile.include_keywords.join(', ') || 'Sin palabras definidas'} · {profile.enabled ? 'Activa' : 'Pausada'}</small></div><div><button onClick={() => edit(profile)}>Editar</button><button className="danger" onClick={() => remove(profile.id)}>Eliminar</button></div></article>)}
      {!profiles.length && <p>Aún no tienes búsquedas programadas.</p>}
    </div></section>

    <section className="panel"><h2>Buscar ahora</h2><form className="search-filters" onSubmit={(event) => search(event, 0)}>
      <label className="wide">Palabra clave<input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Ej. servicio, mantención, equipos" /></label>
      <label>Tipo<select value={searchFilters.opportunity_type} onChange={(e) => setSearchFilters((old) => ({ ...old, opportunity_type: e.target.value }))}><option value="all">Todas</option><option value="licitacion">Licitaciones</option><option value="compra_agil">Compras ágiles</option></select></label>
      <label>Región<input value={searchFilters.region} onChange={(e) => setSearchFilters((old) => ({ ...old, region: e.target.value }))} /></label>
      <label>Organismo<input value={searchFilters.organization} onChange={(e) => setSearchFilters((old) => ({ ...old, organization: e.target.value }))} /></label>
      <label>Estado<input value={searchFilters.status} onChange={(e) => setSearchFilters((old) => ({ ...old, status: e.target.value }))} /></label>
      <div className="actions"><button disabled={loading}>{loading ? 'Buscando…' : 'Buscar'}</button></div>
    </form>
      <div className="result-summary"><strong>{total.toLocaleString('es-CL')} resultados</strong>{total > 0 && <span>Página {page + 1} de {Math.ceil(total / pageSize)}</span>}</div>
      <div className="results">{items.map((item) => <article key={item.id}><strong>{item.title}</strong><p>{item.organization || 'Sin organismo'} · {item.region || 'Sin región'}</p><small>{item.opportunity_type} · {item.status || 'Sin estado'} {item.closing_date ? `· Cierra ${new Date(item.closing_date).toLocaleString('es-CL')}` : ''}</small>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Ver oportunidad</a>}</article>)}</div>
      {total > pageSize && <nav className="pagination" aria-label="Paginación"><button className="secondary" disabled={loading || page === 0} onClick={() => search(null, page - 1)}>Anterior</button><button disabled={loading || (page + 1) * pageSize >= total} onClick={() => search(null, page + 1)}>Siguiente</button></nav>}
    </section>
  </main>;
}
