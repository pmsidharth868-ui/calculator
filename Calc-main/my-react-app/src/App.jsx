import { useState } from 'react'; 
import axios from 'axios';
import './App.css';

const SCHEME_OPTIONS = [
  'MNL1', 'MNL10', 'MNL12', 'MNL21', 
  'MTP5', 'MTP10', 'MTP20', 
  'MSP03', 'MSP04'
];

function App() {
  const [scheme, setScheme] = useState('');
  const [pledgeValue, setPledgeValue] = useState(0);
  const [pledgeDate, setPledgeDate] = useState('');
  const [rows, setRows] = useState([{ Date: '', ad_Charges: 0.0, Credit: 0.0 }]);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleRowChange = (index, field, value) => {
    const updatedRows = [...rows];
    updatedRows[index][field] = value;
    setRows(updatedRows);
  };

  const addRow = () => {
    setRows([...rows, { Date: '', ad_Charges: 0.0, Credit: 0.0 }]);
  };

  const deleteRow = () => {
    if (rows.length > 1) {
      setRows(rows.slice(0, -1));
    }
  };

  const formatToBackendDate = (dateString) => {
    if (!dateString) return '';
    if (dateString.includes('/')) return dateString;
    const [year, month, day] = dateString.split('-');
    return `${day}/${month}/${year}`;
  };

  const getFallbackDate = () => {
    const today = new Date();
    return `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`;
  };

  const handleCalculate = async () => {
    if (!scheme) {
      setError("Please select a scheme first.");
      return;
    }

    setError('');
    setResults(null);

    try {
      const normalizedRows = rows
        .map((row) => ({
          Date: formatToBackendDate(row.Date) || formatToBackendDate(pledgeDate) || getFallbackDate(),
          ad_Charges: parseFloat(row.ad_Charges) || 0,
          Credit: parseFloat(row.Credit) || 0,
        }))
        .filter((row) => row.Date);

      if (normalizedRows.length === 0) {
        normalizedRows.push({
          Date: formatToBackendDate(pledgeDate) || getFallbackDate(),
          ad_Charges: 0,
          Credit: 0,
        });
      }

      const response = await axios.post('/api/calculate', {
        scheme: scheme,
        pledge_value: parseFloat(pledgeValue),
        pledge_date: formatToBackendDate(pledgeDate) || getFallbackDate(),
        input_df: normalizedRows,
      });

      setResults(response.data);
    } catch (err) {
      const backendError =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        "An error occurred connecting to the API";
      console.error("Full Axios Error Object:", err);
      setError(backendError);
    }
  };

  return (
    <div className="app-container">
      <h1>Gold Loan Pledge Calculator 2.0 - NEW</h1>
      
      <div className="input-group">
        <div className="input-field">
          <label>Scheme</label>
          <select value={scheme} onChange={(e) => setScheme(e.target.value)}>
            <option value="" disabled>Select a Scheme</option>
            {SCHEME_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>
        <div className="input-field">
          <label>Pledge Value (₹)</label>
          <input type="number" value={pledgeValue} onChange={(e) => setPledgeValue(e.target.value)} />
        </div>
        <div className="input-field">
          <label>Pledge Date</label>
          <input type="date" value={pledgeDate} onChange={(e) => setPledgeDate(e.target.value)} />
        </div>
      </div>

      <hr />
      
      <h3>Payment Intervals</h3>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Additional Charges</th>
            <th>Credit</th>  
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              <td>
                <input 
                  type="date"
                  value={row.Date} 
                  onChange={(e) => handleRowChange(index, 'Date', e.target.value)} 
                />
              </td>
              <td>
                <input 
                  type="number" 
                  value={row.ad_Charges} 
                  onChange={(e) => handleRowChange(index, 'ad_Charges', e.target.value)} 
                />
              </td>
              <td>
                <input 
                  type="number" 
                  value={row.Credit} 
                  onChange={(e) => handleRowChange(index, 'Credit', e.target.value)} 
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="button-group">
        <button onClick={addRow}>+ Add Row</button>
        <button onClick={deleteRow}>- Delete Last</button>
        <button className="btn-calculate" onClick={handleCalculate}>Calculate</button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {results?.data?.length > 0 && (
        <div className="results-container">
          <h3 className="success-msg">{results.message}</h3>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Opening Balance</th>
                <th>Interest</th>
                <th>Service Charge</th>
                <th>Overdue</th>
                <th>Additional Charge</th>
                <th>Credit Amount</th>
                <th>Rebate</th>
                <th>Closing Balance</th>
              </tr>
            </thead>
            <tbody>
              {results.data.map((res, i) => (
                <tr key={i}>
                  <td>{res.Date}</td>
                  <td>{res["opening balance"] ?? res.opening_balance ?? '-'}</td>
                  <td>{res.Interest}</td>
                  <td>{res["Service Charge"]}</td>
                  <td>{res.Overdue}</td>
                  <td>{res["Additional Charge"]}</td>
                  <td>{res["Credit Amount"]}</td>
                  <td>{res.Rebate !== undefined ? res.Rebate : '-'}</td>
                  <td>{res["closing balance"] ?? res.closing_balance ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;