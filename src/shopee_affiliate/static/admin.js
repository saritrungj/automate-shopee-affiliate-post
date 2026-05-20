function normalize(text) {
  return text.toLowerCase().trim();
}

function initDataTable(table) {
  const wrapper = table.closest(".table-card");
  if (!wrapper || wrapper.querySelector(".data-table-toolbar")) return;

  const toolbar = document.createElement("div");
  toolbar.className = "data-table-toolbar";

  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Search table...";
  search.setAttribute("aria-label", "Search table");

  const count = document.createElement("span");
  count.className = "table-count";

  toolbar.append(search, count);
  wrapper.insertBefore(toolbar, table);

  const tbody = table.tBodies[0];
  const allRows = Array.from(tbody.rows);
  const empty = document.createElement("tr");
  empty.className = "empty-row";
  const emptyCell = document.createElement("td");
  emptyCell.colSpan = table.tHead.rows[0].cells.length;
  emptyCell.textContent = "No matching records";
  empty.appendChild(emptyCell);

  function visibleRows() {
    return allRows.filter((row) => row.style.display !== "none");
  }

  function update() {
    const query = normalize(search.value);
    let shown = 0;
    allRows.forEach((row) => {
      const match = normalize(row.innerText).includes(query);
      row.style.display = match ? "" : "none";
      if (match) shown += 1;
    });
    if (shown === 0 && !tbody.contains(empty)) tbody.appendChild(empty);
    if (shown > 0 && tbody.contains(empty)) tbody.removeChild(empty);
    count.textContent = `${shown} of ${allRows.length} rows`;
  }

  search.addEventListener("input", update);

  Array.from(table.tHead.rows[0].cells).forEach((header, index) => {
    header.title = "Sort";
    header.addEventListener("click", () => {
      const direction = header.dataset.direction === "asc" ? "desc" : "asc";
      Array.from(table.tHead.rows[0].cells).forEach((cell) => {
        delete cell.dataset.direction;
      });
      header.dataset.direction = direction;
      const rows = visibleRows().sort((a, b) => {
        const av = normalize(a.cells[index]?.innerText || "");
        const bv = normalize(b.cells[index]?.innerText || "");
        return direction === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach((row) => tbody.appendChild(row));
    });
  });

  update();
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".data-table").forEach(initDataTable);

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(message)) event.preventDefault();
    });
  });
});
