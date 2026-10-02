const sampleParts = [
  { part: "CBL-USB4-01", type: "Partial FMD", rohs: "Approved", reach: "Data gap", pfas: "Data gap", overall: "Data gap" },
  { part: "PCB-CHG-204", type: "Full FMD", rohs: "Approved", reach: "Approved", pfas: "Approved", overall: "Approved" },
  { part: "ADP-65W-11", type: "Evidence only", rohs: "Condition", reach: "Data gap", pfas: "Data gap", overall: "Data gap" }
];
const queueItems = [
  ["Cable jacket — PFAS intentional use unknown", "CBL-USB4-01 · supplier follow-up required", ""],
  ["Adapter enclosure — material mass missing", "ADP-65W-11 · composition cannot be evaluated", "blocked"],
  ["RoHS exemption 7(c)-I expires in 74 days", "PCB-CHG-204 · reviewer confirmation required", ""]
];
const statusClass = value => ({ "Approved":"approved", "Condition":"condition", "Data gap":"data-gap", "Blocked":"blocked" }[value] || "data-gap");
function render() {
  document.querySelector("#bomRows").innerHTML = sampleParts.map(p => `<tr><td>${p.part}</td><td>${p.type}</td><td><span class="status ${statusClass(p.rohs)}">${p.rohs}</span></td><td><span class="status ${statusClass(p.reach)}">${p.reach}</span></td><td><span class="status ${statusClass(p.pfas)}">${p.pfas}</span></td><td><span class="status ${statusClass(p.overall)}">${p.overall}</span></td></tr>`).join("");
  const template = document.querySelector("#queueTemplate"); const queue = document.querySelector("#reviewQueue"); queue.innerHTML = "";
  queueItems.forEach(([title, detail, kind]) => { const item = template.content.cloneNode(true); item.querySelector(".severity").classList.add(kind); item.querySelector("strong").textContent = title; item.querySelector("small").textContent = detail; item.querySelector("button").addEventListener("click", () => alert(`Demo Preview:\n\n${title}\n\nDisplays required fields, source evidence, and supplier remediation tasks.`)); queue.appendChild(item); });
}
function analyseCsv(text, name) {
  const rows = text.trim().split(/\r?\n/); const headers = (rows[0] || "").split(",").map(x => x.trim()); const required = ["material_name","material_mass_g","cas","concentration_pct","pfas_intentional_use"]; const missing = required.filter(x => !headers.includes(x));
  const valid = Math.max(rows.length - 1, 0); const result = document.querySelector("#importResult"); result.hidden = false;
  result.innerHTML = missing.length ? `<strong>Parsed ${name}</strong>, but cannot submit: missing columns <b>${missing.join(", ")}</b>.` : `<strong>Parsed ${name}</strong>: found ${valid} substance declarations. Quality gate flagged 2 data gaps: PFAS supporting evidence, material mass balance.`;
}
document.querySelector("#csvUpload").addEventListener("change", e => { const file = e.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => analyseCsv(reader.result, file.name); reader.readAsText(file); });
document.querySelector("#loadSample").addEventListener("click", () => analyseCsv("material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use\nCable jacket,8.3,9002-84-0,99.3,Unknown\nCopper conductor,12.4,7440-50-8,99.9,No", "synthetic-usbc-cable-fmd.csv"));
document.querySelector("#downloadTemplate").addEventListener("click", () => { const csv = "material_name,material_mass_g,cas,concentration_pct,pfas_intentional_use\n"; const blob = new Blob([csv], {type:"text/csv"}); const a = Object.assign(document.createElement("a"), {href:URL.createObjectURL(blob),download:"fmd-intake-template.csv"}); a.click(); URL.revokeObjectURL(a.href); });
document.querySelector("#resetDemo").addEventListener("click", () => { document.querySelector("#importResult").hidden = true; document.querySelector("#csvUpload").value = ""; });
render();
