document.addEventListener('DOMContentLoaded', () => {
  let data = [];

  // Capture state and district from URL query parameters
  const params = new URLSearchParams(window.location.search);
  const state = document.getElementById("state-name").textContent.trim();
  const district = document.getElementById("district-name").textContent.trim();
  

  // Display state and district
  document.getElementById('state-name').textContent = state || 'N/A';
  document.getElementById('district-name').textContent = district || 'N/A';
  const excelUrl = document.body.getAttribute('data-excel-url');

fetch(excelUrl)

  // Load Excel file
      .then(r => r.arrayBuffer())
      .then(buffer => {
          const wb = XLSX.read(buffer, { type: 'buffer' });
          const sheet = wb.Sheets[wb.SheetNames[0]];
          const raw = XLSX.utils.sheet_to_json(sheet);

          // Trim whitespace on keys & values
          data = raw.map(row => {
              const o = {};
              for (let k in row) {
                  const kk = k.trim();
                  let v = row[k];
                  if (typeof v === 'string') v = v.trim();
                  o[kk] = v;
              }
              return o;
          });

          // Filter data based on state and district
          const filtered = data.filter(d =>
            d.State?.trim().toLowerCase() === state.toLowerCase() &&
            d.District?.trim().toLowerCase() === district.toLowerCase()
        );
        
          // Render results
          const results = document.getElementById('results');
          if (filtered.length === 0) {
              results.innerHTML = '<p>No blood banks found in this area.</p>';
              return;
          }

          const table = document.createElement('table');
          const thead = document.createElement('thead');
          const headers = [
              'Blood Bank Name', 'City', 'Address', 'Contact No', 'Blood Component Available'
          ];
          const tr = document.createElement('tr');
          headers.forEach(h => {
              const th = document.createElement('th');
              th.textContent = h;
              tr.appendChild(th);
          });
          thead.appendChild(tr);
          table.appendChild(thead);

          const tbody = document.createElement('tbody');
          filtered.forEach(item => {
              const row = document.createElement('tr');
              row.innerHTML = `
                <td>
                    <a href="/map?lat=${item.Latitude}&lng=${item.Longitude}&name=${encodeURIComponent(item['Blood Bank Name'] || '')}" target="_blank">
                    ${item['Blood Bank Name'] || 'N/A'}
                    </a>
                </td>
                <td>${item.City || 'N/A'}</td>
                <td>${item.Address || 'N/A'}</td>
                <td>${item['Contact No'] || 'N/A'}</td>
                <td>${item['Blood Component Available'] || 'N/A'}</td>
                `;

              tbody.appendChild(row);
          });
          table.appendChild(tbody);
          results.appendChild(table);
      })
      .catch(err => {
          document.getElementById('results').innerHTML = '<p class="error">Failed to load data.</p>';
          console.error(err);
      });
});
results.innerHTML = '<p id="loading">Loading nearby blood banks...</p>';
// After data loaded
results.innerHTML = '';
