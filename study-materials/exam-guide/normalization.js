// The diagrams remain readable without JavaScript. Only the study controls need it.
(() => {
  const guide = document.querySelector('[data-norm-guide]');
  if (!guide) return;
  const find = selector => guide.querySelector(selector);
  const all = selector => Array.from(guide.querySelectorAll(selector));
  const tabs = all('[data-norm-tab]');
  const panels = all('[data-norm-panel]');
  let active = '1nf';
  let showAll = false;
  function show(key, focus = false) {
    active = key;
    for (const panel of panels) panel.hidden = !showAll && panel.dataset.normPanel !== active;
    for (const tab of tabs) {
      const selected = tab.dataset.normTab === active;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
    if (focus) find(`[data-norm-tab="${active}"]`).focus();
  }
  for (const tab of tabs) {
    tab.addEventListener('click', () => {
      if (showAll) setAll(false);
      show(tab.dataset.normTab);
    });
    tab.addEventListener('keydown', event => {
      const index = tabs.indexOf(tab);
      let next;
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      if (showAll) setAll(false);
      show(tabs[next].dataset.normTab, true);
    });
  }
  function setAll(value) {
    showAll = value;
    guide.classList.toggle('norm-all', showAll);
    find('[data-norm-all]').setAttribute('aria-pressed', String(showAll));
    find('[data-norm-all]').textContent = showAll ? '단계별로 한 장씩 보기' : '전체 과정을 한 번에 보기';
    show(active);
  }
  find('[data-norm-all]').addEventListener('click', () => setAll(!showAll));
  for (const button of all('[data-norm-go]')) button.addEventListener('click', () => {
    show(button.dataset.normGo, true);
    find('.norm-navigation').scrollIntoView({ block: 'start', behavior: 'auto' });
  });
  for (const button of all('[data-norm-focus]')) button.addEventListener('click', () => {
    find('[data-norm-focus-table]').dataset.focus = button.dataset.normFocus;
    for (const other of all('[data-norm-focus]')) other.setAttribute('aria-pressed', String(other === button));
  });
  function bindChange(buttonSelector, cellsSelector, value, original, resultSelector, changedText, originalText) {
    let changed = false;
    const button = find(buttonSelector);
    const label = button.textContent;
    button.addEventListener('click', () => {
      changed = !changed;
      for (const cell of all(cellsSelector)) {
        cell.textContent = changed ? value : original;
        cell.classList.toggle('norm-changed', changed);
      }
      button.textContent = changed ? '원래 값으로 되돌리기' : label;
      find(resultSelector).textContent = changed ? changedText : originalText;
    });
  }
  bindChange('[data-norm-rename]', '[data-norm-name]', '준호', '민수', '[data-norm-rename-result]',
    '분리 전 수강표: 민수였던 2칸을 모두 수정. 분리 후 학생표: S1 이름 1칸만 수정하면 끝입니다.',
    '위 표의 2칸과 아래 학생표의 1칸을 비교해 보세요.');
  bindChange('[data-norm-change-phone]', '[data-norm-phone]', '9999', '1111', '[data-norm-phone-result]',
    '분리 전 과목표: DB와 Python의 전화 2칸을 모두 수정. 분리 후 강사표: T1의 전화 1칸만 수정하면 끝입니다.',
    '분리 전 2칸과 분리 후 1칸을 비교해 보세요.');
  let added = false;
  find('[data-norm-add-hobby]').addEventListener('click', event => {
    added = !added;
    for (const row of all('[data-norm-extra-hobby]')) row.hidden = !added;
    find('[data-norm-product-count]').textContent = added ? '3 × 2 = 6행' : '2 × 2 = 4행';
    find('[data-norm-hobby-result]').textContent = added ? '분리 전: 수영·영어, 수영·일본어의 2행 추가. 분리 후: 학생 취미표에 S1·수영 1행만 추가합니다.' : '취미 하나를 더 저장할 때, 어느 표에 몇 행이 늘어날까요?';
    event.currentTarget.textContent = added ? '수영을 빼고 원래 표로 돌아가기' : '취미 수영을 추가해 보기';
  });
  // Read the pairs from the visible relation tables so the exercise follows the example.
  function readPairs(name) {
    return new Set(all(`[data-norm-relation="${name}"] tbody tr`).map(row =>
      Array.from(row.cells, cell => cell.textContent.trim()).join('|')));
  }
  const supplierParts = readPairs('supplier-part-5nf');
  const supplierProjects = readPairs('supplier-project-5nf');
  const partProjects = readPairs('part-project-5nf');
  function join() {
    const supplier = find('[data-norm-join="supplier"]').value;
    const part = find('[data-norm-join="part"]').value;
    const project = find('[data-norm-join="project"]').value;
    const checks = [
      ['sp', '① 부품 취급', `${supplier} · ${part}`, supplierParts.has(`${supplier}|${part}`)],
      ['sj', '② 현장 거래', `${supplier} · ${project}`, supplierProjects.has(`${supplier}|${project}`)],
      ['pj', '③ 현장의 부품', `${part} · ${project}`, partProjects.has(`${part}|${project}`)]
    ];
    for (const [key, label, pair, allowed] of checks) {
      const box = find(`[data-norm-join-check="${key}"]`);
      box.replaceChildren(document.createTextNode(label));
      const line = document.createElement('b');
      line.textContent = `${pair} ${allowed ? '✓ 있음' : '✕ 없음'}`;
      box.append(line);
      box.className = allowed ? 'norm-good' : 'norm-warn';
    }
    const allowed = checks.every(check => check[3]);
    find('[data-norm-join-result]').textContent = allowed
      ? `${supplier} · ${part} · ${project} → 세 조건 모두 맞음. 원래 납품표에 있는 행입니다.`
      : `${supplier} · ${part} · ${project} → 없는 관계가 있어 제외. 원래 납품표에 없는 행입니다.`;
  }
  for (const select of all('[data-norm-join]')) select.addEventListener('change', join);
  join();
  for (const quiz of all('[data-norm-quiz]')) {
    for (const button of Array.from(quiz.querySelectorAll('[data-norm-answer]'))) button.addEventListener('click', () => {
      for (const other of quiz.querySelectorAll('[data-norm-answer]')) other.setAttribute('aria-pressed', String(other === button));
      const feedback = quiz.querySelector('[data-norm-feedback]');
      feedback.textContent = (button.dataset.normAnswer === 'right' ? '맞았습니다. ' : '현재 단계와 분리 목표를 다시 비교하세요. ') + feedback.dataset.explanation;
    });
  }
  for (const control of all('.norm-navigation, .norm-focus-buttons, [data-norm-experiment], [data-norm-join-lab]')) control.hidden = false;
  guide.classList.add('norm-ready');
  show(active);
})();
