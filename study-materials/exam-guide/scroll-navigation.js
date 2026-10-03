// Embedded in each generated HTML so local files also work without a server.
(() => {
  const links = Array.from(document.querySelectorAll('.sidebar nav a[href^="#"]'));
  const chapters = links.map(link => ({
    link,
    section: document.getElementById(link.getAttribute('href').slice(1))
  })).filter(chapter => chapter.section);
  if (!chapters.length) return;

  let active = null;
  let queued = false;
  function update() {
    queued = false;
    const visible = chapters.filter(chapter => chapter.section.getClientRects().length);
    if (!visible.length) {
      active = null;
      links.forEach(link => link.removeAttribute('aria-current'));
      return;
    }
    const readingLine = Math.min(160, Math.max(64, window.innerHeight * 0.18));
    let current = visible[0];
    for (const chapter of visible) {
      if (chapter.section.getBoundingClientRect().top <= readingLine) current = chapter;
    }
    const page = document.scrollingElement;
    if (page && window.scrollY + window.innerHeight >= page.scrollHeight - 2) {
      current = visible[visible.length - 1];
    }
    if (active === current.link) return;
    active = current.link;
    links.forEach(link => {
      if (link === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function schedule() {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(update);
  }
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  window.addEventListener('pageshow', schedule);
  document.addEventListener('toggle', schedule, true);
  links.forEach(link => link.addEventListener('click', schedule));
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(schedule);
    observer.observe(document.querySelector('main'));
  }
  update();
})();
