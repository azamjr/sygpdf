// Page previews and ordering stay entirely in the browser.
(() => {
  'use strict';
  let generation = 0, documentHandle = null, observer = null, dragCard = null;
  const grid = () => document.querySelector('#page-grid');
  const status = () => document.querySelector('#page-status');

  function announce(message) { if (status()) status().textContent = message; }
  function count() {
    const n = grid()?.children.length || 0;
    announce(n ? `${n} page${n === 1 ? '' : 's'} selected. Drag to reorder, or use the arrow buttons.` : 'No pages selected. Reset to restore them.');
  }
  function reset() {
    generation++;
    observer?.disconnect(); observer = null; dragCard = null;
    if (documentHandle) { documentHandle.destroy().catch(() => {}); documentHandle = null; }
  }
  async function preview(card, doc, token) {
    if (card.dataset.rendered) return;
    card.dataset.rendered = '1';
    try {
      const page = await doc.getPage(Number(card.dataset.page));
      if (token !== generation || !card.isConnected) return;
      const scale = Math.min(150 / page.view[2], 195 / page.view[3]);
      const viewport = page.getViewport({ scale: Math.max(scale, .05) });
      const canvas = card.querySelector('canvas');
      canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
      await page.render({ canvasContext: canvas.getContext('2d', { alpha: false }), viewport }).promise;
      page.cleanup();
      if (token === generation) card.classList.add('preview-ready');
    } catch (e) { card.dataset.rendered = ''; card.querySelector('.preview-fallback').textContent = 'Preview unavailable'; }
  }
  function makeCard(page, doc, token) {
    const card = document.createElement('div');
    card.className = 'page-card'; card.dataset.page = page; card.draggable = true;
    card.setAttribute('aria-label', `Page ${page}`);
    card.innerHTML = '<div class="page-preview"><canvas aria-hidden="true"></canvas><span class="preview-fallback">Page ' + page + '</span></div>' +
      '<div class="page-caption"><span>Page ' + page + '</span><button type="button" class="drag-handle" aria-label="Drag page ' + page + '" title="Drag to reorder">⠿</button></div>' +
      '<div class="page-buttons"><button type="button" data-step="-1" aria-label="Move page ' + page + ' earlier">←</button><button type="button" data-step="1" aria-label="Move page ' + page + ' later">→</button><button type="button" data-delete aria-label="Remove page ' + page + '">×</button></div>';
    card.querySelectorAll('[data-step]').forEach(button => button.onclick = () => {
      const neighbor = button.dataset.step === '-1' ? card.previousElementSibling : card.nextElementSibling;
      if (!neighbor) return;
      if (button.dataset.step === '-1') grid().insertBefore(card, neighbor);
      else grid().insertBefore(neighbor, card);
      button.focus(); count();
    });
    card.querySelector('[data-delete]').onclick = () => { observer?.unobserve(card); card.remove(); count(); };
    observer.observe(card);
    return card;
  }
  function moveNear(card, target, clientX, clientY) {
    if (!target || target === card) return;
    const rect = target.getBoundingClientRect();
    const before = Math.abs(clientY - (rect.top + rect.height / 2)) > Math.abs(clientX - (rect.left + rect.width / 2))
      ? clientY < rect.top + rect.height / 2 : clientX < rect.left + rect.width / 2;
    grid().insertBefore(card, before ? target : target.nextSibling);
  }
  function bindDragging(container) {
    if (!container.dataset.dragBound) {
    container.dataset.dragBound = '1';
    container.addEventListener('dragstart', e => {
      if (e.target.closest('button')) { e.preventDefault(); return; }
      dragCard = e.target.closest('.page-card');
      if (!dragCard) return;
      e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', dragCard.dataset.page);
      requestAnimationFrame(() => dragCard?.classList.add('dragging'));
    });
    container.addEventListener('dragover', e => {
      if (!dragCard) return;
      e.preventDefault(); e.dataTransfer.dropEffect = 'move';
      moveNear(dragCard, e.target.closest('.page-card'), e.clientX, e.clientY);
    });
    container.addEventListener('drop', e => { if (dragCard) { e.preventDefault(); count(); } });
    container.addEventListener('dragend', () => { dragCard?.classList.remove('dragging'); dragCard = null; count(); });
    }
    // Native HTML dragging does not work reliably on touchscreens.
    container.querySelectorAll('.drag-handle').forEach(handle => {
      let active = null;
      handle.addEventListener('pointerdown', e => {
        if (e.pointerType === 'mouse') return;
        e.preventDefault(); active = handle.closest('.page-card'); handle.setPointerCapture(e.pointerId);
        active.classList.add('dragging');
      });
      handle.addEventListener('pointermove', e => {
        if (!active) return;
        const target = document.elementFromPoint(e.clientX, e.clientY)?.closest('.page-card');
        moveNear(active, target, e.clientX, e.clientY);
      });
      const finish = () => { if (active) { active.classList.remove('dragging'); active = null; count(); } };
      handle.addEventListener('pointerup', finish); handle.addEventListener('pointercancel', finish);
    });
  }
  async function load(file) {
    reset();
    const token = generation, container = grid();
    if (!container || !file) return;
    container.replaceChildren(); announce('Loading pages and previews…');
    try {
      const pdfjs = await import('/assets/pdfjs.min.mjs');
      pdfjs.GlobalWorkerOptions.workerSrc = '/assets/pdfjs.worker.min.mjs';
      const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) });
      const doc = await task.promise;
      if (token !== generation) { await doc.destroy(); return; }
      documentHandle = doc;
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => { if (entry.isIntersecting) { observer.unobserve(entry.target); preview(entry.target, doc, token); } });
      }, { rootMargin: '200px' });
      const fragment = document.createDocumentFragment();
      for (let page = 1; page <= doc.numPages; page++) fragment.append(makeCard(page, doc, token));
      container.append(fragment); bindDragging(container); count();
    } catch (error) {
      if (token === generation) announce('Could not load page previews: ' + (error.message || 'Invalid PDF.'));
    }
  }
  function getPages() {
    const pages = [...(grid()?.children || [])].map(card => Number(card.dataset.page));
    if (!documentHandle) throw Error('Wait for the PDF pages to load before processing.');
    if (!pages.length) throw Error('Keep at least one page, or reset the page list.');
    return pages.join(',');
  }
  function restore(file) { if (file) load(file); }
  window.organizeUI = { load, reset, getPages, restore };
})();
