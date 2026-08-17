function inferRepoUrl() {
  const host = window.location.hostname;
  const path = window.location.pathname.split('/').filter(Boolean);

  if (host.endsWith('.github.io')) {
    const owner = host.split('.')[0];
    const repo = path[0];
    if (repo) return `https://github.com/${owner}/${repo}`;
    return `https://github.com/${owner}`;
  }

  return '#';
}

const repo = inferRepoUrl();
['repoLink', 'repoButton', 'bottomRepo'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.href = repo;
});

document.querySelectorAll('.copy').forEach(button => {
  button.addEventListener('click', async () => {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;

    const text = target.innerText;
    try {
      await navigator.clipboard.writeText(text);
      const old = button.textContent;
      button.textContent = 'Copiado';
      setTimeout(() => button.textContent = old, 1200);
    } catch {
      button.textContent = 'Selecione e copie';
    }
  });
});
