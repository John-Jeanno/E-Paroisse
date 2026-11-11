document.addEventListener('DOMContentLoaded', () => {
  const filters = document.querySelector('#changelist-filter');
  if (!filters || !window.matchMedia('(max-width: 900px)').matches) {
    return;
  }

  filters.querySelectorAll('details[open]').forEach((filter) => {
    filter.open = false;
  });
});
