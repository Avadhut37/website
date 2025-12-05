import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export default function App() {
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async () => {
    try {
      const res = await axios.get(`${API_URL}/items`);
      setItems(res.data);
    } catch (err) {
      console.error('Error fetching items:', err);
    } finally {
      setLoading(false);
    }
  };

  const addItem = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    
    try {
      await axios.post(`${API_URL}/items`, { title, description });
      setTitle('');
      setDescription('');
      fetchItems();
    } catch (err) {
      console.error('Error adding item:', err);
    }
  };

  const deleteItem = async (id) => {
    try {
      await axios.delete(`${API_URL}/items/${id}`);
      fetchItems();
    } catch (err) {
      console.error('Error deleting item:', err);
    }
  };

  return (
    <div style={ padding: '2rem', maxWidth: '800px', margin: '0 auto' }>
      <h1 style={ marginBottom: '1.5rem', color: '#333' }>Linktree Clone</h1>
      
      <form onSubmit={addItem} style={ marginBottom: '2rem', padding: '1rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          style={ width: '100%', padding: '0.5rem', marginBottom: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }
        />
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          style={ width: '100%', padding: '0.5rem', marginBottom: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }
        />
        <button type="submit" style={ padding: '0.5rem 1rem', background: '#0070f3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }>
          Add Item
        </button>
      </form>

      {loading ? (
        <p>Loading...</p>
      ) : items.length === 0 ? (
        <p style={ color: '#666' }>No items yet. Add one above!</p>
      ) : (
        <ul style={ listStyle: 'none' }>
          {items.map(item => (
            <li key={item.id} style={ padding: '1rem', marginBottom: '0.5rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }>
              <div>
                <strong>{item.title}</strong>
                {item.description && <p style={ color: '#666', fontSize: '0.9rem' }>{item.description}</p>}
              </div>
              <button onClick={() => deleteItem(item.id)} style={ padding: '0.25rem 0.5rem', background: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
