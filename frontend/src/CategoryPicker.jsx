import { useMemo } from 'react';

const SEGMENT_NAMES = {
  10: 'Material vegetal, animal y accesorios', 11: 'Minerales, textiles y materiales no comestibles',
  12: 'Químicos, bioquímicos y gases', 13: 'Resinas, caucho, espuma y películas',
  14: 'Papel y productos de papel', 15: 'Combustibles, lubricantes y anticorrosivos',
  20: 'Maquinaria de minería y perforación', 21: 'Maquinaria agrícola, pesquera y forestal',
  22: 'Maquinaria de construcción', 23: 'Maquinaria de fabricación industrial',
  24: 'Manipulación, almacenaje y embalaje', 25: 'Vehículos y sus componentes',
  26: 'Generación y distribución de energía', 27: 'Herramientas y maquinaria general',
  30: 'Componentes y suministros de construcción', 31: 'Componentes y suministros de fabricación',
  32: 'Componentes electrónicos', 39: 'Iluminación y material eléctrico',
  40: 'Climatización y distribución de fluidos', 41: 'Laboratorio, medición y pruebas',
  42: 'Equipos y suministros médicos', 43: 'Tecnologías de información y telecomunicaciones',
  44: 'Equipos y suministros de oficina', 45: 'Impresión, fotografía y audiovisuales',
  46: 'Seguridad, defensa y vigilancia', 47: 'Limpieza y suministros de aseo',
  48: 'Maquinaria para servicios', 49: 'Deportes y recreación',
  50: 'Alimentos, bebidas y tabaco', 51: 'Medicamentos y productos farmacéuticos',
  52: 'Artículos y electrodomésticos domésticos', 53: 'Ropa, equipaje y cuidado personal',
  54: 'Relojería, joyería y piedras preciosas', 55: 'Publicaciones y material impreso',
  56: 'Muebles y decoración', 60: 'Instrumentos, juegos, educación y arte',
  70: 'Servicios agrícolas, pesqueros y forestales', 71: 'Servicios de minería, petróleo y gas',
  72: 'Construcción y mantenimiento', 73: 'Producción y manufactura industrial',
  76: 'Servicios de limpieza industrial', 77: 'Servicios medioambientales',
  78: 'Transporte, almacenaje y correo', 80: 'Gestión, administración y servicios empresariales',
  81: 'Ingeniería, investigación y tecnología', 82: 'Servicios editoriales, diseño y artes gráficas',
  83: 'Servicios públicos y telecomunicaciones', 84: 'Servicios financieros y seguros',
  85: 'Servicios de salud', 86: 'Educación y capacitación',
  90: 'Viajes, alimentación, alojamiento y entretenimiento', 91: 'Servicios personales y domésticos',
  92: 'Defensa, orden público y seguridad', 93: 'Política y administración pública',
  94: 'Organizaciones y asociaciones', 95: 'Terrenos, edificios y estructuras',
};

const LEVELS = { 2: 'Rubro general', 4: 'Familia', 6: 'Clase', 8: 'Producto específico' };
const tokenFor = (prefix) => `${prefix}*`;
const prefixOf = (value) => value.endsWith('*') ? value.slice(0, -1) : value;

function branchLabel(prefix) {
  if (prefix.length === 2) return SEGMENT_NAMES[prefix] || `Rubro general ${prefix}`;
  return `${LEVELS[prefix.length]} ${prefix}`;
}

function makeTree(categories) {
  const segments = new Map();
  categories.forEach((category) => {
    const code = String(category.code || '').replace(/\D/g, '').padStart(8, '0');
    if (code.length !== 8) return;
    const keys = [code.slice(0, 2), code.slice(0, 4), code.slice(0, 6)];
    const path = String(category.name || '').split('/').map((part) => part.trim()).filter(Boolean);
    if (!segments.has(keys[0])) segments.set(keys[0], { name: '', families: new Map() });
    const segment = segments.get(keys[0]);
    if (path.length >= 3) segment.name = path[0];
    if (!segment.families.has(keys[1])) segment.families.set(keys[1], { name: '', classes: new Map() });
    const family = segment.families.get(keys[1]);
    if (path.length >= 3) family.name = path[1];
    if (!family.classes.has(keys[2])) family.classes.set(keys[2], { name: '', products: [] });
    const classItem = family.classes.get(keys[2]);
    if (path.length >= 3) classItem.name = path[2];
    if (!code.endsWith('00')) classItem.products.push({ ...category, code });
  });
  return segments;
}

function categoryLevel(code) {
  if (code.endsWith('000000')) return 'Rubro general';
  if (code.endsWith('0000')) return 'Familia';
  if (code.endsWith('00')) return 'Clase';
  return 'Producto específico';
}

function selectionValue(code) {
  if (code.endsWith('000000')) return tokenFor(code.slice(0, 2));
  if (code.endsWith('0000')) return tokenFor(code.slice(0, 4));
  if (code.endsWith('00')) return tokenFor(code.slice(0, 6));
  return code;
}

function treeBranchName(tree, prefix) {
  const segment = tree.get(prefix.slice(0, 2));
  if (prefix.length === 2) return segment?.name;
  const family = segment?.families.get(prefix.slice(0, 4));
  if (prefix.length === 4) return family?.name;
  return family?.classes.get(prefix.slice(0, 6))?.name;
}

function SelectButton({ prefix, selected, toggle }) {
  const token = tokenFor(prefix);
  const active = selected.includes(token);
  return <button type="button" className={`branch-select${active ? ' selected' : ''}`} onClick={() => toggle(token)}>{active ? 'Seleccionado' : 'Seleccionar todo'}</button>;
}

export default function CategoryPicker({ categories, selected, search, onSearch, toggle }) {
  const tree = useMemo(() => makeTree(categories), [categories]);
  const query = search.trim().toLowerCase();
  const matches = query ? categories.filter((item) => `${item.code} ${item.name}`.toLowerCase().includes(query)) : [];
  const selectedItems = selected.map((value) => {
    const exact = categories.find((item) => item.code === value);
    if (exact) return { value, name: exact.name.split('/').pop().trim(), level: categoryLevel(String(exact.code)) };
    const prefix = prefixOf(value);
    return { value, name: treeBranchName(tree, prefix) || branchLabel(prefix), level: LEVELS[prefix.length] || 'Categoría' };
  });

  return <fieldset className="category-picker wide">
    <legend>Rubros de Mercado Público</legend>
    <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Buscar transversalmente por nombre o código ONU" />
    {selectedItems.length > 0 && <div className="selected-categories" aria-label="Rubros seleccionados">{selectedItems.map((item) => <button key={item.value} type="button" className="selected-tag" onClick={() => toggle(item.value)} title="Quitar rubro"><span><small>{item.level}</small>{item.name}</span><b aria-hidden="true">×</b></button>)}</div>}

    {query ? <div className="category-search-results">
      <p><strong>Resultados en todas las ramas</strong><small>{matches.length} coincidencias</small></p>
      {matches.map((category) => { const code = String(category.code); const value = selectionValue(code); const active = selected.includes(value); const path = category.name.split('/').map((part) => part.trim()); return <button key={category.code} type="button" className={`category-tag${active ? ' selected' : ''}`} onClick={() => toggle(value)}><span>{path.at(-1)}</span><small>{categoryLevel(code)} · {path.length > 1 ? path.join(' › ') : `${code.slice(0, 2)} › ${code.slice(0, 4)} › ${code.slice(0, 6)} › ${code}`}</small></button>; })}
      {!matches.length && <p>No se encontraron rubros con ese nombre o código.</p>}
    </div> : <div className="category-tree">
      {[...tree].map(([segmentCode, segment]) => <details key={segmentCode} className="tree-segment"><summary><span><small>Rubro general</small>{segment.name || branchLabel(segmentCode)} <b>{[...segment.families.values()].reduce((sum, family) => sum + [...family.classes.values()].reduce((count, classItem) => count + Math.max(classItem.products.length, 1), 0), 0}</b></span></summary><div className="tree-branch"><SelectButton prefix={segmentCode} selected={selected} toggle={toggle} />{[...segment.families].map(([familyCode, family]) => <details key={familyCode}><summary><span><small>Familia</small>{family.name || branchLabel(familyCode)}</span></summary><div className="tree-branch"><SelectButton prefix={familyCode} selected={selected} toggle={toggle} />{[...family.classes].map(([classCode, classItem]) => <details key={classCode}><summary><span><small>Clase</small>{classItem.name || branchLabel(classCode)} <b>{classItem.products.length}</b></span></summary><div className="tree-products"><SelectButton prefix={classCode} selected={selected} toggle={toggle} />{classItem.products.map((product) => <button key={product.code} type="button" className={`category-tag${selected.includes(product.code) ? ' selected' : ''}`} onClick={() => toggle(product.code)}><span>{product.name}</span><small>Producto específico · {product.code}</small></button>)}</div></details>)}</div></details>)}</div></details>)}
      {!categories.length && <p>Aún no hay rubros catalogados. El enriquecimiento continúa automáticamente.</p>}
    </div>}
    <small>{selected.length} selecciones · Una selección general incluye todos los niveles inferiores.</small>
  </fieldset>;
}
