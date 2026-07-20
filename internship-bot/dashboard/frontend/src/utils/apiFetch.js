export const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem('token');
  
  const headers = {
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  // If token is invalid/expired
  if (response.status === 401 && !url.includes('/auth/login')) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }

  return response;
};
