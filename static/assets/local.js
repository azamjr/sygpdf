function selectedPages(text, count) {
  if (!String(text || '').trim()) return Array.from({length: count}, (_, i) => i);
  const pages = [];
  for (const part of String(text).split(',')) {
    const match = part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) throw Error('Use page numbers or ranges, such as 3,1-2.');
    const start = Number(match[1]), end = Number(match[2] || match[1]);
    if (Math.min(start,end) < 1 || Math.max(start,end) > count) throw Error('A selected page is outside this document.');
    const step = end < start ? -1 : 1;
    for (let n = start; ; n += step) {
      if (pages.length >= 5000) throw Error('Choose up to 5,000 pages.');
      pages.push(n - 1);
      if (n === end) break;
    }
  }
  return pages;
}
window.processInBrowser = async function(tool, files, opts) {
  const { PDFDocument, degrees } = PDFLib;
  const docs = [];
  for (const file of files) docs.push(await PDFDocument.load(await file.arrayBuffer()));
  let output;
  if (tool === 'rotate') {
    output = docs[0];
    const angle = Number(opts.degrees || 90);
    for (const i of new Set(selectedPages(opts.pages,output.getPageCount()))) {
      const page = output.getPage(i);
      page.setRotation(degrees((page.getRotation().angle + angle) % 360));
    }
  } else {
    output = await PDFDocument.create();
    for (const doc of docs) {
      const pages = tool === 'organize' ? selectedPages(opts.pages,doc.getPageCount()) : doc.getPageIndices();
      for (const page of await output.copyPages(doc,pages)) output.addPage(page);
    }
  }
  return {filename:tool + '.pdf',blob:new Blob([await output.save()], {type:'application/pdf'})};
};
