<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login | FinParse</title>
    <link rel="stylesheet" href="index.css?v=4">
</head>
<body style="display: flex; align-items: center; justify-content: center; min-height: 100vh;">
    <div class="auth-box">
        <div class="logo" style="justify-content: center; margin-bottom: 20px; font-size: 24px;">
            <span class="logo-icon" style="padding: 4px 10px;">_</span> FINPARSE
        </div>
        <h2>Sign In</h2>
        <p style="color: var(--text-light); text-align: center; margin-bottom: 30px;">Welcome back to your dashboard</p>
        
        <input type="email" id="authEmail" class="auth-input" placeholder="Email Address" required>
        <input type="password" id="authPassword" class="auth-input" placeholder="Password" required>
        
        <button id="authBtn" class="auth-btn">Log In</button>
        
        <div id="authStatus" style="color: #ef4444; margin-top: 10px; font-size: 14px; text-align: center;"></div>
        
        <div style="margin-top: 20px; text-align: center; font-size: 14px; color: var(--text-light);">
            Don't have an account? <a href="signup.html" style="color: var(--primary); text-decoration: none; font-weight: bold;">Sign Up</a>
        </div>
    </div>
    <script src="auth.js?v=4" data-mode="login"></script>
</body>
</html>
