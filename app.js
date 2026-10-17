/* قصر العطور — كتالوج قابل للتصفية (RTL / عربي)
   مصدر البيانات: products.json (مبني من متجر perfumespalace.store عبر build-products.py) */

(() => {
  'use strict';

  /* ---------- أدوات مساعدة ---------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // تطبيع النص العربي لتحسين البحث: إزالة التشكيل وتوحيد الألف والياء والتاء المربوطة.
  const norm = (s) => String(s)
    .replace(/[\u064B-\u0652\u0640]/g, '')
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .toLowerCase();

  const locale = () => (DATA.meta && DATA.meta.locale) || 'ar-EG-u-nu-latn';

  // كسور عند الحاجة فقط: 140 ₪ و 140.50 ₪ في التنسيق نفسه.
  const money = (n) =>
    new Intl.NumberFormat(locale(), {
      style: 'currency',
      currency: DATA.meta.currency || 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(n);

  // null في price يعني «السعر عند الطلب» ولا يدخل في مؤشر السعر.
  const priceText = (p) => (p.price == null ? 'السعر عند الطلب' : money(p.price));

  const label = (key) => String(key).replace(/-/g, ' ');

  const stars = (r) => {
    const full = Math.round(r);
    return '★★★★★'.slice(0, full) + '☆☆☆☆☆'.slice(0, 5 - full);
  };

  const isSale = (p) => p.compare_at_price != null && p.price != null && p.compare_at_price > p.price;
  const discount = (p) => isSale(p) ? Math.round((1 - p.price / p.compare_at_price) * 100) : 0;

  // WooCommerce يخفي الكميات الدقيقة: 0 = نفدت، null = متوفرة بكمية غير معلنة.
  const soldOut = (p) => p.stock === 0;
  const lowStock = (p) => typeof p.stock === 'number' && p.stock > 0 && p.stock <= 8;

  // بديل محلي آمن إذا فشل رابط الصورة.
  const placeholder = (p) => {
    const hue = [...p.name].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
    const initials = p.name.split(/\s+/).slice(0, 2).map((w) => w[0]).join('');
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="hsl(${hue},32%,80%)"/><stop offset="1" stop-color="hsl(${(hue + 45) % 360},30%,62%)"/>
      </linearGradient></defs>
      <rect width="400" height="400" fill="url(#g)"/>
      <text x="200" y="220" font-family="Georgia,serif" font-size="110" fill="rgba(255,255,255,.72)"
            text-anchor="middle">${initials}</text></svg>`;
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  };

  const imgTag = (p, cls = '', eager = false) =>
    `<img class="${cls}" src="${esc(p.images[0])}" alt="${esc(p.name)}" loading="${eager ? 'eager' : 'lazy'}"${eager ? ' fetchpriority="high"' : ''}
      data-fallback="${esc(placeholder(p))}"
      onerror="this.onerror=null;this.src=this.dataset.fallback">`;

  /* ---------- الحالة ---------- */
  const state = {
    q: '',
    brands: new Set(),
    categories: new Set(),
    attrs: {},          // مفتاح الخاصية -> مجموعة القيم
    min: 0,
    max: 0,
    sale: false,
    inStock: false,
    minRating: 0,
    sort: 'featured',
    view: 'grid',
  };

  let DATA = { meta: {}, products: [] };
  let FACETS = {};
  let bounds = { min: 0, max: 0 };
  let hasRatings = false;   // بعض المتاجر لا تحمل أي تقييمات — تُخفى مجموعة التقييم
  let newestAdded = '';     // مرجع شارة «جديد»: أحدث منتج في الكتالوج
  const CART_KEY = 'northline_cart';
  const MAX_QTY = 99;

  // السلة: معرّف المنتج -> الكمية. تُحفظ في التخزين المحلي وتُعاد قراءتها عند التشغيل.
  function readCart() {
    const map = new Map();
    try {
      const raw = JSON.parse(localStorage.getItem(CART_KEY) || '{}');
      Object.entries(raw).forEach(([id, qty]) => {
        const n = Math.round(Number(qty));
        if (Number.isFinite(n) && n > 0) map.set(Number(id), Math.min(MAX_QTY, n));
      });
    } catch { map.clear(); }
    localStorage.removeItem('northline_cart_count'); // نسخة قديمة كانت تخزن عدداً فقط
    return map;
  }

  let cart = readCart();

  // الخاصية قد تحمل عدة قيم (الموسم: خريفي، ربيعي، شتوي) فتُحفظ كمصفوفة في JSON.
  const attrValues = (p, key) => {
    const v = p.attributes && p.attributes[key];
    if (v == null) return [];
    return Array.isArray(v) ? v : [v];
  };
  const attrDisplay = (p, key) => attrValues(p, key).join('، ');

  /* ---------- اكتشاف عوامل التصفية من البيانات ---------- */
  function buildFacets() {
    const products = DATA.products;

    const count = (predicate) => {
      const map = new Map();
      for (const p of products) {
        const key = predicate(p);
        if (key == null) continue;
        (Array.isArray(key) ? key : [key]).forEach((k) => map.set(k, (map.get(k) || 0) + 1));
      }
      return map;
    };

    FACETS.brand = count((p) => p.brand);
    FACETS.category = count((p) => p.category);

    // كل مفتاح خصائص موجود في JSON يصبح مجموعة تصفية مستقلة.
    const keys = new Map();
    for (const p of products) {
      for (const k of Object.keys(p.attributes || {})) {
        keys.set(k, (keys.get(k) || 0) + 1);
      }
    }
    FACETS.attrKeys = [...keys.entries()]
      .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), locale()))
      .map(([k]) => k);

    FACETS.attrs = {};
    for (const k of FACETS.attrKeys) {
      FACETS.attrs[k] = count((p) => (p.attributes && p.attributes[k]) || null);
    }
    // الخاصية ذات القيمة الواحدة لا تصفي شيئاً — تُتجاهل.
    FACETS.attrKeys = FACETS.attrKeys.filter((k) => FACETS.attrs[k].size > 1);

    for (const k of FACETS.attrKeys) {
      if (!state.attrs[k]) state.attrs[k] = new Set();
    }

    const prices = products.map((p) => p.price).filter((n) => typeof n === 'number');
    const lo = prices.length ? Math.floor(Math.min(...prices) / 10) * 10 : 0;
    const hi = prices.length ? Math.ceil(Math.max(...prices) / 10) * 10 : 0;
    bounds = { min: lo, max: hi };
    state.min = lo;
    state.max = hi;

    hasRatings = products.some((p) => Number(p.reviews) > 0);
    newestAdded = products.map((p) => p.added).filter(Boolean).sort().reverse()[0]
      || DATA.meta.updated || '';
  }

  /* ---------- التصفية ---------- */
  function textMatch(p) {
    const attrs = Object.keys(p.attributes || {}).flatMap((k) => attrValues(p, k));
    const hay = norm([p.name, p.brand, p.category, p.sku, p.description,
      ...(p.tags || []), ...attrs].join(' '));
    return norm(state.q).split(/\s+/).filter(Boolean).every((w) => hay.includes(w));
  }

  // skip: اسم المجموعة التي يتم تجاهلها في الحساب، لتظهر الأعداد «ماذا سيحدث لو اخترت هذا».
  function matches(p, skip) {
    if (skip !== 'brand' && state.brands.size && !state.brands.has(p.brand)) return false;
    if (skip !== 'category' && state.categories.size && !state.categories.has(p.category)) return false;

    for (const [key, set] of Object.entries(state.attrs)) {
      if (key === skip || !set.size) continue;
      if (!attrValues(p, key).some((v) => set.has(v))) return false;
    }

    const priced = typeof p.price === 'number';
    if (skip !== 'price' && priced && (p.price < state.min || p.price > state.max)) return false;
    if (skip !== 'sale' && state.sale && !isSale(p)) return false;
    if (skip !== 'stock' && state.inStock && soldOut(p)) return false;
    if (skip !== 'rating' && state.minRating && p.rating < state.minRating) return false;
    if (state.q && !textMatch(p)) return false;
    return true;
  }

  function sortProducts(list) {
    const by = {
      'price-asc': (a, b) => (a.price ?? Infinity) - (b.price ?? Infinity),
      'price-desc': (a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity),
      rating: (a, b) => b.rating - a.rating || b.reviews - a.reviews,
      newest: (a, b) => b.added.localeCompare(a.added),
      name: (a, b) => String(a.name).localeCompare(String(b.name), locale()),
      featured: (a, b) =>
        (Number(isSale(b)) - Number(isSale(a))) ||
        (b.rating * Math.log10(b.reviews + 1) - a.rating * Math.log10(a.reviews + 1)) ||
        b.added.localeCompare(a.added),
    };
    return list.sort(by[state.sort] || by.featured);
  }

  /* ---------- واجهة التصفية ---------- */
  function chevron() {
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
  }

  function facetShell(title, key, bodyHtml, collapsed = false, scroll = false) {
    return `<div class="facet${collapsed ? ' collapsed' : ''}${scroll ? ' is-scroll' : ''}" data-facet="${esc(key)}">
      <button class="facet-head" type="button" aria-expanded="${collapsed ? 'false' : 'true'}">
        <span class="facet-title">${esc(title)}</span>${chevron()}
      </button>
      <div class="facet-body">${bodyHtml}</div>
    </div>`;
  }

  function facetCount(group, value) {
    if (group === 'brand') return DATA.products.filter((p) => p.brand === value && matches(p, 'brand')).length;
    if (group === 'category') return DATA.products.filter((p) => p.category === value && matches(p, 'category')).length;
    if (group.startsWith('attr:')) {
      const key = group.slice(5);
      return DATA.products.filter((p) => attrValues(p, key).includes(value) && matches(p, key)).length;
    }
    if (group === 'sale') return DATA.products.filter((p) => isSale(p) && matches(p, 'sale')).length;
    if (group === 'stock') return DATA.products.filter((p) => !soldOut(p) && matches(p, 'stock')).length;
    if (group === 'rating') return DATA.products.filter((p) => p.rating >= Number(value) && matches(p, 'rating')).length;
    return 0;
  }

  function checkRow(group, value, n, checked) {
    return `<label class="check${n === 0 && !checked ? ' is-empty' : ''}">
      <input type="checkbox" data-group="${esc(group)}" value="${esc(value)}" ${checked ? 'checked' : ''}>
      <span>${esc(value)}</span><span class="n">${n}</span>
    </label>`;
  }

  // حقول طويلة مثل العلامات التجارية (49 قيمة) تحتاج بحثاً داخل المجموعة نفسها.
  const LONG_GROUP = 12;
  const facetSearch = (placeholder) =>
    `<input class="facet-search" type="search" placeholder="${esc(placeholder)}"
      aria-label="${esc(placeholder)}" autocomplete="off">
     <p class="facet-empty" hidden>لا تطابق في هذه المجموعة</p>`;

  function valueRows(group, values, selected, searchPlaceholder) {
    const rows = values.map((v) => checkRow(group, v, facetCount(group, v), selected.has(v))).join('');
    return (values.length > LONG_GROUP ? facetSearch(searchPlaceholder) : '') + rows;
  }

  function renderFilters() {
    const groups = [];

    // العلامات الأكثر منتجاتٍ أولاً ثم أبجدياً.
    const brandValues = [...FACETS.brand.keys()].sort((a, b) =>
      (FACETS.brand.get(b) - FACETS.brand.get(a)) || String(a).localeCompare(String(b), locale()));
    groups.push(facetShell('العلامة التجارية', 'brand',
      valueRows('brand', brandValues, state.brands, 'بحث في العلامات التجارية'),
      false, brandValues.length > LONG_GROUP));

    const categoryValues = [...FACETS.category.keys()]
      .sort((a, b) => String(a).localeCompare(String(b), locale()));
    groups.push(facetShell('الفئة', 'category',
      valueRows('category', categoryValues, state.categories, 'بحث في الفئات'),
      false, categoryValues.length > LONG_GROUP));

    const priceBody = `
      <div class="price-ui">
        <div class="price-values"><b id="pv-min"></b><b id="pv-max"></b></div>
        <div class="range">
          <div class="track"></div><div class="fill" id="p-fill"></div>
          <input id="price-min" type="range" min="${bounds.min}" max="${bounds.max}" step="5" value="${state.min}" aria-label="أقل سعر">
          <input id="price-max" type="range" min="${bounds.min}" max="${bounds.max}" step="5" value="${state.max}" aria-label="أعلى سعر">
        </div>
        <div class="price-inputs">
          <input id="price-min-field" type="number" min="${bounds.min}" max="${bounds.max}" step="1" value="${state.min}" aria-label="أقل سعر">
          <input id="price-max-field" type="number" min="${bounds.min}" max="${bounds.max}" step="1" value="${state.max}" aria-label="أعلى سعر">
        </div>
      </div>`;
    groups.push(facetShell('السعر', 'price', priceBody));

    const availBody = `
      <label class="check"><input type="checkbox" data-group="sale" ${state.sale ? 'checked' : ''}><span>عليها تخفيضات</span>
        <span class="n">${facetCount('sale', '')}</span></label>
      <label class="check"><input type="checkbox" data-group="stock" ${state.inStock ? 'checked' : ''}><span>متوفر في المخزون</span>
        <span class="n">${facetCount('stock', '')}</span></label>`;
    groups.push(facetShell('التوفر', 'availability', availBody));

    if (hasRatings) {
      const ratingBody = [4.5, 4.0, 3.5].map((r) => `
        <label class="check"><input type="checkbox" data-group="rating" value="${r}" ${state.minRating === r ? 'checked' : ''}>
          <span>${r.toFixed(1)} وأعلى ★</span>
          <span class="n">${facetCount('rating', r)}</span></label>`).join('');
      groups.push(facetShell('التقييم', 'rating', ratingBody));
    }

    // الخصائص المخصصة مأخوذة مباشرة من JSON.
    for (let i = 0; i < FACETS.attrKeys.length; i++) {
      const key = FACETS.attrKeys[i];
      const values = [...FACETS.attrs[key].keys()].sort((a, b) =>
        String(a).localeCompare(String(b), locale(), { numeric: true }));
      const body = valueRows('attr:' + key, values, state.attrs[key], `بحث في ${label(key)}`);
      const collapsed = i >= 6 || values.length > 14;
      groups.push(facetShell(label(key), key, body, collapsed, values.length > LONG_GROUP));
    }

    $('#facet-groups').innerHTML = groups.join('');
    syncPriceUI();
  }

  function refreshFacets() {
    $$('#facet-groups input[type=checkbox]').forEach((input) => {
      const group = input.dataset.group;
      const value = input.value;
      let on = false;
      if (group === 'brand') on = state.brands.has(value);
      else if (group === 'category') on = state.categories.has(value);
      else if (group.startsWith('attr:')) on = !!state.attrs[group.slice(5)]?.has(value);
      else if (group === 'sale') on = state.sale;
      else if (group === 'stock') on = state.inStock;
      else if (group === 'rating') on = state.minRating === Number(value);
      input.checked = on;
      const row = input.closest('.check');
      if (row) {
        const n = row.querySelector('.n');
        const total = facetCount(group, value);
        if (n) n.textContent = total;
        row.classList.toggle('is-empty', total === 0 && !on);
      }
    });
  }

  function syncPriceUI() {
    const pvMin = $('#pv-min'), pvMax = $('#pv-max');
    if (pvMin) pvMin.textContent = money(state.min);
    if (pvMax) pvMax.textContent = money(state.max);
    const lo = $('#price-min'), hi = $('#price-max');
    if (lo) lo.value = state.min;
    if (hi) hi.value = state.max;
    const fMin = $('#price-min-field'), fMax = $('#price-max-field');
    if (fMin) fMin.value = state.min;
    if (fMax) fMax.value = state.max;
    const fill = $('#p-fill');
    if (fill) {
      const span = bounds.max - bounds.min || 1;
      // خصائص منطقية حتى يعمل المؤشر بشكل صحيح في الاتجاهين LTR و RTL.
      fill.style.insetInlineStart = ((state.min - bounds.min) / span * 100) + '%';
      fill.style.insetInlineEnd = ((bounds.max - state.max) / span * 100) + '%';
    }
  }

  function activeFilters() {
    const chips = [];
    state.brands.forEach((v) => chips.push({ group: 'brand', value: v, text: v }));
    state.categories.forEach((v) => chips.push({ group: 'category', value: v, text: v }));
    for (const [key, set] of Object.entries(state.attrs)) {
      set.forEach((v) => chips.push({ group: 'attr:' + key, value: v, text: `${label(key)}: ${v}` }));
    }
    if (state.min > bounds.min || state.max < bounds.max) {
      chips.push({ group: 'price', value: '', text: `${money(state.min)} – ${money(state.max)}` });
    }
    if (state.sale) chips.push({ group: 'sale', value: '', text: 'عليها تخفيضات' });
    if (state.inStock) chips.push({ group: 'stock', value: '', text: 'متوفر' });
    if (state.minRating) chips.push({ group: 'rating', value: String(state.minRating), text: `${state.minRating.toFixed(1)} وأعلى ★` });
    if (state.q) chips.push({ group: 'q', value: '', text: `«${state.q}»` });
    return chips;
  }

  function renderChips() {
    const chips = activeFilters();
    $('#active-chips').innerHTML = chips.map((c) =>
      `<span class="chip">${esc(c.text)}<button type="button" data-group="${esc(c.group)}" data-value="${esc(c.value)}" aria-label="إزالة التصفية">
        <svg viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18"/></svg></button></span>`).join('');
    // الرقائق مثبَّتة في الشريط؛ يظهر زر «مسح الكل» معها فقط.
    $('.chips-row').hidden = chips.length === 0;
    $('#chips-clear').hidden = chips.length === 0;
  }

  /* ---------- بطاقات المنتجات ---------- */
  function isNew(p) {
    // المتجر يؤرّخ المنتج برفع صورته، فالمرجع هو أحدث منتج في الكتالوج لا تاريخ بناء الملف.
    const days = (new Date(newestAdded) - new Date(p.added)) / 86400000;
    return days <= 30;
  }

  function cardHtml(p) {
    const specs = Object.keys(p.attributes || {}).slice(0, 3)
      .map((k) => `<li>${esc(label(k))}: ${esc(attrDisplay(p, k))}</li>`).join('');
    const badges = [];
    if (isSale(p)) badges.push(`<span class="badge sale">خصم ${discount(p)}%</span>`);
    if (isNew(p)) badges.push('<span class="badge new">جديد</span>');
    if (soldOut(p)) badges.push('<span class="badge sold">نفدت الكمية</span>');
    else if (lowStock(p)) badges.push(`<span class="badge low">بقي ${p.stock} فقط</span>`);

    return `<article class="card" data-id="${p.id}">
      <div class="card-media">
        <button class="media-open" type="button" data-quick="${p.id}"
                aria-label="عرض تفاصيل «${esc(p.name)}»">
          ${imgTag(p)}
          <span class="quick" aria-hidden="true">عرض تفاصيل المنتج</span>
        </button>
        <div class="badges">${badges.join('')}</div>
      </div>
      <div class="card-body">
        <p class="brand">${esc(p.brand)}</p>
        <h3 class="title">${esc(p.name)}</h3>
        ${hasRatings ? `<div class="stars"><span class="glyph">${stars(p.rating)}</span> ${p.rating.toFixed(1)} · ${p.reviews} تقييم</div>` : ''}
        <ul class="specs">${specs}</ul>
        <p class="desc">${esc(p.description)}</p>
        <div class="card-foot">
          <div class="price">
            <span class="now${p.price == null ? ' on-request' : ''}">${priceText(p)}</span>
            ${isSale(p) ? `<span class="was">${money(p.compare_at_price)}</span>` : ''}
          </div>
          <button class="add" type="button" data-add="${p.id}" ${soldOut(p) ? 'disabled' : ''}>
            ${soldOut(p) ? 'نفدت الكمية' : 'أضف'}
          </button>
        </div>
      </div>
    </article>`;
  }

  function skeleton() {
    return `<div class="skeleton"><div class="sk-img"></div><div class="sk-line" style="width:45%"></div>
      <div class="sk-line" style="width:80%"></div><div class="sk-line" style="width:60%"></div></div>`;
  }

  function render() {
    const list = sortProducts(DATA.products.filter((p) => matches(p)));
    const grid = $('#grid');
    grid.className = 'grid' + (state.view === 'list' ? ' list-view' : '');
    grid.innerHTML = list.map(cardHtml).join('');

    const empty = $('#empty');
    empty.hidden = list.length > 0;

    const saleCount = list.filter(isSale).length;
    $('#count').innerHTML = `<b>${list.length}</b> منتج${saleCount ? ` · منها <b>${saleCount}</b> بتخفيضات` : ''}`;
    renderChips();
    persistState();
    syncAddButtons();
  }

  /* ---------- نافذة التفاصيل ---------- */
  function openModal(id) {
    const p = DATA.products.find((x) => x.id === Number(id));
    if (!p) return;
    const images = p.images && p.images.length ? p.images : [null];
    const rows = Object.keys(p.attributes || {})
      .map((k) => `<tr><th>${esc(label(k))}</th><td>${esc(attrDisplay(p, k))}</td></tr>`).join('');
    const meta = DATA.meta || {};
    const links = [];
    if (p.url) links.push(`<a class="text-link" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">فتح المنتج في المتجر</a>`);
    if (meta.whatsapp) links.push(`<a class="text-link" href="https://wa.me/${esc(String(meta.whatsapp).replace(/\D/g, ''))}" target="_blank" rel="noopener noreferrer">اطلب عبر واتساب</a>`);

    $('#modal-body').innerHTML = `<div class="modal-grid">
      <div class="gallery">
        <div class="main">${imgTag(p)}</div>
        ${images.length > 1 ? `<div class="thumbs">${images.map((src, i) =>
          `<button type="button" data-thumb="${i}" class="${i === 0 ? 'is-active' : ''}" aria-label="صورة ${i + 1}">
            <img src="${esc(src)}" alt="" loading="lazy" data-fallback="${esc(placeholder(p))}"
              onerror="this.onerror=null;this.src=this.dataset.fallback"></button>`).join('')}</div>` : ''}
      </div>
      <div class="detail">
        <p class="brand">${esc(p.brand)} · <span class="sku">${esc(p.sku)}</span></p>
        <h2 id="modal-title">${esc(p.name)}</h2>
        ${hasRatings ? `<div class="stars"><span class="glyph">${stars(p.rating)}</span> ${p.rating.toFixed(1)} من ${p.reviews} تقييماً</div>` : ''}
        <p class="desc">${esc(p.description)}</p>
        <div class="price">
          <span class="now${p.price == null ? ' on-request' : ''}">${priceText(p)}</span>
          ${isSale(p) ? `<span class="was">${money(p.compare_at_price)}</span>
            <span class="badge sale">خصم ${discount(p)}%</span>` : ''}
        </div>
        <p class="stock-line ${soldOut(p) ? 'out' : ''}"><span class="dot"></span>${
          soldOut(p) ? 'نفدت الكمية' : (p.stock == null ? 'متوفر' : `متوفر (${p.stock})`)}</p>
        <table class="spec-table"><tbody>${rows}</tbody></table>
        <button class="btn" type="button" data-add="${p.id}" ${soldOut(p) ? 'disabled' : ''}>
          ${soldOut(p) ? 'نفدت الكمية' : 'أضف إلى السلة'}</button>
        ${links.length ? `<p class="modal-links">${links.join(' · ')}</p>` : ''}
        <div class="tags">${(p.tags || []).map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>
      </div>
    </div>`;

    $('#modal').hidden = false;
    syncAddButtons();
    lockScroll();

    $$('#modal .thumbs button').forEach((btn) => {
      btn.addEventListener('click', () => {
        const src = images[Number(btn.dataset.thumb)];
        const main = $('#modal .gallery .main img');
        main.src = src;
        main.onerror = () => { main.src = placeholder(p); };
        $$('#modal .thumbs button').forEach((b) => b.classList.toggle('is-active', b === btn));
      });
    });
  }

  function closeModal() {
    $('#modal').hidden = true;
    lockScroll();
  }

  /* ---------- السلة ---------- */
  const cartUnits = () => [...cart.values()].reduce((a, b) => a + b, 0);

  function cartLines() {
    const lines = [];
    cart.forEach((qty, id) => {
      const p = DATA.products.find((x) => x.id === id);
      if (p) lines.push({ p, qty });
    });
    return lines;
  }

  function saveCart() {
    const obj = {};
    cart.forEach((qty, id) => { obj[id] = qty; });
    localStorage.setItem(CART_KEY, JSON.stringify(obj));
    $('#cart-count').textContent = cartUnits();
    syncAddButtons();
    renderCart();
  }

  function addToCart(id, delta = 1) {
    const p = DATA.products.find((x) => x.id === Number(id));
    if (!p || soldOut(p)) return;
    const qty = (cart.get(p.id) || 0) + delta;
    if (qty <= 0) cart.delete(p.id);
    else cart.set(p.id, Math.min(MAX_QTY, qty));
    saveCart();
    if (delta > 0) toast(`تمت إضافة «${p.name}» إلى السلة`);
  }

  function removeLine(id) {
    const p = DATA.products.find((x) => x.id === Number(id));
    cart.delete(Number(id));
    saveCart();
    if (p) toast(`أُزيل «${p.name}» من السلة`);
  }

  function clearCart() {
    if (!cart.size) return;
    cart.clear();
    saveCart();
    toast('مسحت السلة');
  }

  // أزرار «أضف» تعكس محتوى السلة الحالي.
  function syncAddButtons() {
    $$('[data-add]').forEach((btn) => {
      const qty = cart.get(Number(btn.dataset.add)) || 0;
      const inCart = qty > 0;
      btn.classList.toggle('has-qty', inCart);
      if (btn.disabled) return;
      const base = btn.closest('.card') ? 'أضف' : 'أضف إلى السلة';
      btn.textContent = inCart ? `في السلة (${qty})` : base;
    });
  }

  function cartWhatsAppUrl(lines, total) {
    const meta = DATA.meta || {};
    const digits = String(meta.whatsapp || '').replace(/\D/g, '');
    if (!digits || !lines.length) return '';
    const rows = lines.map(({ p, qty }) =>
      `• ${p.name} (${p.sku}) × ${qty} — ${p.price == null ? 'السعر عند الطلب' : money(p.price * qty)}`);
    const text = `طلب من كتالوج ${meta.store || 'الكتالوج'}:\n${rows.join('\n')}\n`
      + `الإجمالي: ${money(total)} · عدد القطع: ${cartUnits()}`;
    return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
  }

  function renderCart() {
    const lines = cartLines();
    const body = $('#cart-body');

    body.innerHTML = lines.length ? lines.map(({ p, qty }) => `
      <div class="cart-line">
        <button class="cart-thumb" type="button" data-quick="${p.id}"
                aria-label="عرض تفاصيل «${esc(p.name)}»">${imgTag(p)}</button>
        <div class="cart-info">
          <p class="name">${esc(p.name)}</p>
          <p class="meta">${esc(p.brand)} · <span class="sku">${esc(p.sku)}</span></p>
          <p class="unit">${priceText(p)}${isSale(p) ? ` <span class="was">${money(p.compare_at_price)}</span>` : ''}</p>
        </div>
        <div class="cart-side">
          <div class="qty">
            <button type="button" data-cart-dec="${p.id}" aria-label="تقليل الكمية">&minus;</button>
            <span>${qty}</span>
            <button type="button" data-cart-inc="${p.id}" aria-label="زيادة الكمية">+</button>
          </div>
          <p class="line-total">${p.price == null ? '—' : money(p.price * qty)}</p>
          <button class="remove" type="button" data-cart-remove="${p.id}">إزالة</button>
        </div>
      </div>`).join('')
      : `<div class="cart-blank"><p>السلة فارغة.</p>
         <p class="hint">اختر منتجاً من الكتالوج ثم اضغط «أضف».</p></div>`;

    const priced = lines.filter((l) => l.p.price != null);
    const total = priced.reduce((a, l) => a + l.p.price * l.qty, 0);
    const saved = priced.reduce((a, l) => a + (isSale(l.p) ? (l.p.compare_at_price - l.p.price) * l.qty : 0), 0);
    const onRequest = lines.length - priced.length;

    $('#cart-lines-label').textContent = lines.length ? `· ${lines.length} منتج` : '';
    $('#cart-units').textContent = cartUnits();
    $('#cart-total').textContent = priced.length ? money(total) : '—';
    $('#cart-save').textContent = money(saved);
    $('#cart-save-row').hidden = saved <= 0;
    $('#cart-request').textContent = `${onRequest} منتج`;
    $('#cart-request-row').hidden = onRequest === 0;

    const url = cartWhatsAppUrl(lines, total);
    const checkout = $('#cart-checkout');
    checkout.href = url;
    checkout.hidden = !url;
    $('#cart-clear').hidden = lines.length === 0;
    $('.cart-foot').hidden = lines.length === 0;
    $('#cart-note').textContent = lines.length
      ? 'يُرسل الطلب إلى المتجر عبر واتساب ليؤكد البائع السعر والتوفر قبل الدفع.' : '';
  }

  function openCart() {
    renderCart();
    $('#cart-drawer').hidden = false;
    lockScroll();
  }

  function closeCart() {
    $('#cart-drawer').hidden = true;
    lockScroll();
  }

  // التمرير مقفل ما دامت نافذة التفاصيل أو السلة مفتوحة.
  function lockScroll() {
    const open = !$('#modal').hidden || !$('#cart-drawer').hidden;
    document.body.style.overflow = open ? 'hidden' : '';
  }

  let toastTimer;
  function toast(msg) {
    const el = $('#toast');
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 2400);
  }

  /* ---------- حالة الرابط ---------- */
  function persistState() {
    const q = new URLSearchParams();
    if (state.q) q.set('q', state.q);
    if (state.brands.size) q.set('brand', [...state.brands].join('|'));
    if (state.categories.size) q.set('cat', [...state.categories].join('|'));
    for (const [k, set] of Object.entries(state.attrs)) {
      if (set.size) q.set('attr.' + k, [...set].join('|'));
    }
    if (state.min > bounds.min) q.set('min', state.min);
    if (state.max < bounds.max) q.set('max', state.max);
    if (state.sale) q.set('sale', '1');
    if (state.inStock) q.set('stock', '1');
    if (state.minRating) q.set('rating', state.minRating);
    if (state.sort !== 'featured') q.set('sort', state.sort);
    if (state.view !== 'grid') q.set('view', state.view);

    const s = q.toString();
    const base = location.href.split('#')[0];
    try { history.replaceState(null, '', s ? '#' + s : base); }
    catch { location.replace(s ? '#' + s : base); }
  }

  function readState() {
    const q = new URLSearchParams(location.hash.replace(/^#/, ''));
    state.q = q.get('q') || '';
    (q.get('brand') || '').split('|').filter(Boolean).forEach((v) => state.brands.add(v));
    (q.get('cat') || '').split('|').filter(Boolean).forEach((v) => state.categories.add(v));
    for (const [k, v] of q.entries()) {
      if (!k.startsWith('attr.')) continue;
      const key = k.slice(5);
      if (!state.attrs[key]) state.attrs[key] = new Set();
      v.split('|').filter(Boolean).forEach((x) => state.attrs[key].add(x));
    }
    if (q.has('min')) state.min = Number(q.get('min'));
    if (q.has('max')) state.max = Number(q.get('max'));
    state.sale = q.get('sale') === '1';
    state.inStock = q.get('stock') === '1';
    state.minRating = Number(q.get('rating') || 0);
    state.sort = q.get('sort') || 'featured';
    state.view = q.get('view') || 'grid';
  }

  /* ---------- الشريط المثبَّت ---------- */
  // ارتفاع الشريط العلوي يتغيّر عند التفافه في الشاشات الضيقة، فيُحسب ويُمرَّر إلى CSS.
  function syncStickyOffset() {
    const bar = $('.topbar');
    if (bar) document.documentElement.style.setProperty('--stick', Math.round(bar.getBoundingClientRect().height) + 'px');
    watchStuck();
  }

  // «is-stuck» عندما يتجاوز المؤشرُ حدَّ التثبيت — يعطي الشريط حداً فاصلاً وظلاً.
  function watchStuck() {
    const head = $('#results-head'), sentinel = $('.stuck-sentinel');
    if (!head || !sentinel) return;
    const limit = parseFloat(getComputedStyle(head).top) || 0;
    head.classList.toggle('is-stuck', sentinel.getBoundingClientRect().top < limit - 1);
  }

  /* ---------- الواجهة العلوية المتحركة ---------- */
  const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  // كلمات الدوّار مشتقة من جملة المتجر نفسها (meta.tagline) بدل نص ثابت.
  function splitTagline(tagline) {
    const text = String(tagline || '').trim();
    const [main, rest] = text.split(/\s+—\s+/);
    const words = (rest || '')
      .split(/[،]\s*و?|\s+و/)
      .map((w) => w.replace(/\s+متوفرة\.?$/, '').replace(/[.،]$/, '').trim())
      .filter((w) => w.length > 1);
    return { main: (main || text || 'عطور أصلية').trim(), words: words.slice(0, 4) };
  }

  // خلط ترتيب مصفوفة في مكانها (Fisher–Yates).
  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  const HERO_SLIDES = 5;

  // صور الواجهة: اختيار عشوائي من المنتجات المتوفرة التي لها صور وسعر،
  // بعلامة تجارية مختلفة لكل شريحة. صور المعارض تأتي أولاً داخل العشوائية لأنها أوضح.
  function heroPicks() {
    const eligible = DATA.products.filter((p) => p.images && p.images.length && p.price != null && !soldOut(p));
    const galleries = shuffle(eligible.filter((p) => p.images.length > 1));
    const singles = shuffle(eligible.filter((p) => p.images.length === 1));
    const seen = new Set();
    const picks = [];
    const take = (list) => {
      for (const p of list) {
        if (picks.length >= HERO_SLIDES) return;
        if (seen.has(p.brand)) continue;
        seen.add(p.brand);
        picks.push(p);
      }
    };
    take(galleries);
    take(singles);
    return picks;
  }

  function heroStats() {
    const products = DATA.products;
    const prices = products.map((p) => p.price).filter((n) => typeof n === 'number' && n > 0);
    return [
      { label: 'منتج في الكتالوج', count: products.length },
      { label: 'علامة تجارية', count: FACETS.brand ? FACETS.brand.size : 0 },
      { label: 'عليها تخفيضات', count: products.filter(isSale).length },
      { label: 'تبدأ من', text: prices.length ? money(Math.min(...prices)) : '—' },
    ];
  }

  // تصاعد الأرقام عند بناء الإحصاءات.
  function countUp(el, target) {
    if (reducedMotion()) { el.textContent = target; return; }
    const dur = 900, t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      el.textContent = Math.round(target * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderHero() {
    const meta = DATA.meta || {};
    const { main, words } = splitTagline(meta.tagline);

    $('#h1-main').textContent = main;
    if (meta.tagline) $('.hero h1').setAttribute('aria-label', meta.tagline);
    const rot = $('#h1-rot');
    const list = reducedMotion() || words.length < 2 ? words.slice(0, 1) : words;
    rot.innerHTML = list.map((w, i) => `<span style="--i:${i}">${esc(w)}</span>`).join('');

    $('#hero-stats').innerHTML = heroStats().map((s) =>
      `<div><dt>${esc(s.label)}</dt><dd${s.count != null ? ` data-count="${s.count}"` : ''}>${esc(s.text || '0')}</dd></div>`
    ).join('');
    $$('#hero-stats dd[data-count]').forEach((dd) => countUp(dd, Number(dd.dataset.count)));

    // شريط العلامات: نسختان من العناصر حتى يكون التمرير مستمراً بلا قفزات.
    const brands = [...FACETS.brand.keys()].slice(0, 18);
    const items = brands.map((b) => `<span class="marquee-item">${esc(b)}</span>`).join('');
    $('#marquee-track').innerHTML = items + items;

    renderHeroSlides();
  }

  function renderHeroSlides() {
    const picks = heroPicks();
    $('#hero-stage').innerHTML = picks.map((p, i) => `
      <button class="hero-slide${i === 0 ? ' is-active' : ''}" type="button" data-quick="${p.id}"
        ${i ? 'tabindex="-1" aria-hidden="true"' : ''} aria-label="عرض تفاصيل «${esc(p.name)}»">
        ${imgTag(p, 'hero-img', i === 0)}
        ${isSale(p) ? `<span class="badge sale">خصم ${discount(p)}%</span>` : ''}
        <span class="hero-caption">
          <span class="hero-cap-brand">${esc(p.brand)}</span>
          <span class="hero-cap-name">${esc(p.name)}</span>
          <span class="hero-cap-price">${priceText(p)}${isSale(p) ? `<s>${money(p.compare_at_price)}</s>` : ''}</span>
        </span>
      </button>`).join('');

    $('#hero-dots').innerHTML = picks.map((p, i) =>
      `<button type="button" class="${i === 0 ? 'is-active' : ''}" data-hero-slide="${i}"
        aria-label="الصورة ${i + 1}: ${esc(p.name)}"></button>`).join('');

    startHeroCarousel();
  }

  // حالة الشريط تبقى هنا لأن الصور تُعاد خلطها دون إعادة ربط الأحداث.
  const heroCarousel = { timer: null, queue: [], current: 0, hovered: false, outOfView: false };

  function heroShow(index) {
    const slides = $$('#hero-stage .hero-slide');
    const dots = $$('#hero-dots button');
    const n = slides.length;
    if (!n) return;
    heroCarousel.current = (index + n) % n;
    slides.forEach((s, k) => {
      s.classList.toggle('is-active', k === heroCarousel.current);
      if (k === heroCarousel.current) { s.removeAttribute('aria-hidden'); s.removeAttribute('tabindex'); }
      else { s.setAttribute('aria-hidden', 'true'); s.tabIndex = -1; }
    });
    dots.forEach((d, k) => d.classList.toggle('is-active', k === heroCarousel.current));
  }

  // الدور التالي عشوائي: طابور من الفهارس المخلوطة يُعاد خلطه كلما فرغ.
  function heroNext() {
    const n = $$('#hero-stage .hero-slide').length;
    if (n < 2) return;
    const queue = heroCarousel.queue;
    if (!queue.length) {
      for (let k = 0; k < n; k++) if (k !== heroCarousel.current) queue.push(k);
      shuffle(queue);
    }
    heroShow(queue.pop());
  }

  // تبديل كل 5.2 ثانية، يتوقف عند التحويم أو الخروج من الشاشة أو إخفاء التبويب.
  function startHeroCarousel() {
    clearInterval(heroCarousel.timer);
    heroCarousel.queue = [];
    heroShow(0);
    const n = $$('#hero-stage .hero-slide').length;
    if (n < 2 || reducedMotion()) return;
    heroCarousel.timer = setInterval(() => {
      if (!heroCarousel.outOfView && !heroCarousel.hovered && !document.hidden) heroNext();
    }, 5200);
  }

  // تحريك الخلفية والصور مع المؤشر (بارالاكس خفيف).
  function bindHeroParallax() {
    if (reducedMotion() || !matchMedia('(pointer: fine)').matches) return;
    const hero = $('#hero');
    let raf = 0, mx = 0, my = 0;

    const apply = () => {
      raf = 0;
      hero.style.setProperty('--mx', mx.toFixed(3));
      hero.style.setProperty('--my', my.toFixed(3));
    };

    hero.addEventListener('pointermove', (e) => {
      const r = hero.getBoundingClientRect();
      mx = (e.clientX - r.left) / r.width - 0.5;
      my = (e.clientY - r.top) / r.height - 0.5;
      if (!raf) raf = requestAnimationFrame(apply);
    });
    hero.addEventListener('pointerleave', () => { mx = 0; my = 0; if (!raf) raf = requestAnimationFrame(apply); });
  }

  function jumpToResults() {
    $('.results').scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' });
  }

  /* ---------- الأحداث ---------- */
  // تصفية صفوف المجموعة نفسها (بحث داخل قائمة العلامات التجارية مثلاً).
  function filterFacetRows(input) {
    const needle = norm(input.value);
    const body = input.closest('.facet-body');
    if (!body) return;
    let shown = 0;
    $$('.check', body).forEach((row) => {
      const hit = !needle || norm(row.textContent).includes(needle);
      row.hidden = !hit;
      if (hit) shown++;
    });
    const note = $('.facet-empty', body);
    if (note) note.hidden = shown > 0;
  }

  function bind() {
    let debounce;

    const search = $('#search');
    search.value = state.q;
    search.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => { state.q = search.value.trim(); render(); }, 180);
    });

    $('#sort').value = state.sort;
    $('#sort').addEventListener('change', (e) => { state.sort = e.target.value; render(); });

    $$('.view-toggle button').forEach((b) => {
      b.classList.toggle('is-active', b.dataset.view === state.view);
      b.addEventListener('click', () => {
        state.view = b.dataset.view;
        $$('.view-toggle button').forEach((x) => x.classList.toggle('is-active', x === b));
        render();
      });
    });

    // تفاعلات التصفية (نيابةً عن الأحداث لأن المحتوى يُعاد رسمه).
    const facetRoot = $('#facet-groups');

    facetRoot.addEventListener('change', (e) => {
      const input = e.target;
      if (input.type !== 'checkbox') return;
      const group = input.dataset.group;

      if (group === 'brand') toggleSet(state.brands, input.value, input.checked);
      else if (group === 'category') toggleSet(state.categories, input.value, input.checked);
      else if (group.startsWith('attr:')) {
        const key = group.slice(5);
        if (!state.attrs[key]) state.attrs[key] = new Set();
        toggleSet(state.attrs[key], input.value, input.checked);
      } else if (group === 'sale') state.sale = input.checked;
      else if (group === 'stock') state.inStock = input.checked;
      else if (group === 'rating') {
        state.minRating = input.checked ? Number(input.value) : 0;
      }
      update();
    });

    facetRoot.addEventListener('click', (e) => {
      const head = e.target.closest('.facet-head');
      if (!head) return;
      const facet = head.closest('.facet');
      facet.classList.toggle('collapsed');
      head.setAttribute('aria-expanded', facet.classList.contains('collapsed') ? 'false' : 'true');
    });

    // مؤشرات السعر وحقول البحث داخل المجموعات الطويلة.
    facetRoot.addEventListener('input', (e) => {
      const box = e.target.closest('.facet-search');
      if (box) { filterFacetRows(box); return; }

      const id = e.target.id;
      if (!id || !id.startsWith('price-')) return;
      if (id === 'price-min' || id === 'price-max') {
        let lo = Number($('#price-min').value);
        let hi = Number($('#price-max').value);
        if (lo > hi) [lo, hi] = [hi, lo];
        state.min = lo; state.max = hi;
        syncPriceUI();
      } else {
        const v = Number(e.target.value);
        if (Number.isNaN(v)) return;
        if (id === 'price-min-field') state.min = Math.max(bounds.min, Math.min(v, state.max));
        else state.max = Math.min(bounds.max, Math.max(v, state.min));
        syncPriceUI();
      }
      clearTimeout(debounce);
      debounce = setTimeout(render, 140);
    });

    // الرقائق والبطاقات والنافذة — على مستوى المستند ليبقى الاتصال بعد إعادة الرسم.
    document.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip button');
      if (chip) { removeFilter(chip.dataset.group, chip.dataset.value); return; }

      const quick = e.target.closest('[data-quick]');
      if (quick) { openModal(quick.dataset.quick); return; }

      const add = e.target.closest('[data-add]');
      if (add) { addToCart(add.dataset.add); return; }

      const inc = e.target.closest('[data-cart-inc]');
      if (inc) { addToCart(inc.dataset.cartInc); return; }

      const dec = e.target.closest('[data-cart-dec]');
      if (dec) { addToCart(dec.dataset.cartDec, -1); return; }

      const remove = e.target.closest('[data-cart-remove]');
      if (remove) { removeLine(remove.dataset.cartRemove); return; }

      if (e.target.closest('[data-cart-close]')) { closeCart(); return; }

      if (e.target.closest('[data-close]')) closeModal();
    });

    $('#cart').addEventListener('click', openCart);
    $('#cart-clear').addEventListener('click', clearCart);

    $('#clear-all').addEventListener('click', clearAll);
    $('#empty-clear').addEventListener('click', clearAll);
    $('#chips-clear').addEventListener('click', clearAll);

    // أزرار الواجهة العلوية
    $('#hero-browse').addEventListener('click', jumpToResults);
    $('#hero-sale').addEventListener('click', () => {
      state.sale = true;
      update();
      jumpToResults();
      toast('طبّقت التصفية: منتجات عليها تخفيضات');
    });

    // أزرار نقاط الصور + زر الخلط (نيابةً عن الأحداث لأن الصور تُعاد بناءها عند الخلط).
    $('#hero-dots').addEventListener('click', (e) => {
      const dot = e.target.closest('[data-hero-slide]');
      if (dot) heroShow(Number(dot.dataset.heroSlide));
    });
    $('#hero-shuffle').addEventListener('click', () => {
      renderHeroSlides();
      toast('خلطنا صور الواجهة');
    });

    // إيقاف التشغيل التلقائي عند التحويم أو خروج القسم من الشاشة.
    const stage = $('#hero-stage');
    const pause = () => { heroCarousel.hovered = true; };
    const resume = () => { heroCarousel.hovered = false; };
    stage.addEventListener('pointerenter', pause);
    stage.addEventListener('pointerleave', resume);
    stage.addEventListener('focusin', pause);
    stage.addEventListener('focusout', resume);
    new IntersectionObserver(([entry]) => { heroCarousel.outOfView = !entry.isIntersecting; }, { threshold: 0 })
      .observe($('#hero'));

    addEventListener('scroll', watchStuck, { passive: true });
    addEventListener('resize', syncStickyOffset);

    $('#filters-toggle').addEventListener('click', () => $('#filters').classList.toggle('open'));

    $('#theme').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem('northline_theme', next);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { closeModal(); closeCart(); $('#filters').classList.remove('open'); }
      if (e.key === '/' && document.activeElement !== $('#search')) {
        e.preventDefault();
        $('#search').focus();
      }
    });
  }

  function toggleSet(set, value, on) {
    if (on) set.add(value); else set.delete(value);
  }

  function removeFilter(group, value) {
    if (group === 'brand') state.brands.delete(value);
    else if (group === 'category') state.categories.delete(value);
    else if (group.startsWith('attr:')) state.attrs[group.slice(5)]?.delete(value);
    else if (group === 'sale') state.sale = false;
    else if (group === 'stock') state.inStock = false;
    else if (group === 'rating') state.minRating = 0;
    else if (group === 'price') { state.min = bounds.min; state.max = bounds.max; }
    else if (group === 'q') { state.q = ''; $('#search').value = ''; }
    update();
  }

  function clearAll() {
    state.q = '';
    state.brands.clear();
    state.categories.clear();
    Object.values(state.attrs).forEach((s) => s.clear());
    state.min = bounds.min;
    state.max = bounds.max;
    state.sale = false;
    state.inStock = false;
    state.minRating = 0;
    $('#search').value = '';
    update();
  }

  function update() {
    refreshFacets();
    syncPriceUI();
    render();
  }

  /* ---------- التشغيل ---------- */
  async function load() {
    const res = await fetch('products.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('products.json أعاد الخطأ ' + res.status);
    const data = await res.json();
    if (!Array.isArray(data.products)) throw new Error('لا بد أن يحتوي products.json على مصفوفة products');
    return data;
  }

  async function init() {
    const savedTheme = localStorage.getItem('northline_theme');
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;
    $('#cart-count').textContent = cartUnits();
    $('#grid').innerHTML = skeleton().repeat(8);

    try {
      DATA = await load();
    } catch (err) {
      $('#count').textContent = 'تعذّر تحميل products.json';
      $('#grid').innerHTML = `<div class="empty"><h3>تعذّر تحميل products.json</h3>
        <p>${esc(err.message)}. المتصفحات تمنع <code>fetch()</code> في صفحات <code>file://</code> — شغّل خادماً محلياً:
        <code>python -m http.server 8000</code> ثم افتح <code>http://localhost:8000</code>.</p></div>`;
      return;
    }

    const meta = DATA.meta || {};
    // تنظيف السلة من منتجات لم تعد في الكتالوج بعد تحديث البيانات.
    const known = new Set(DATA.products.map((p) => p.id));
    [...cart.keys()].forEach((id) => { if (!known.has(id)) cart.delete(id); });
    saveCart();

    document.title = `${meta.store || 'الكتالوج'} — الكتالوج`;
    $('.logo-text').innerHTML = esc(meta.store || 'الكتالوج').replace(/\s+(\S+)$/, ' <em>$1</em>');
    $('#updated').textContent = new Date(meta.updated || Date.now())
      .toLocaleDateString(locale(), { month: 'long', day: 'numeric', year: 'numeric' });

    buildFacets();
    readState();
    state.min = Math.max(bounds.min, Math.min(state.min, bounds.max));
    state.max = Math.min(bounds.max, Math.max(state.max, bounds.min));
    FACETS.attrKeys.forEach((k) => { if (!state.attrs[k]) state.attrs[k] = new Set(); });

    renderFilters();
    bind();
    update();
    renderHero();
    bindHeroParallax();
    syncStickyOffset();
  }

  init();
})();
