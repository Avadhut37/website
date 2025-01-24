import app, { auth } from './config.js';
import { initializeAppCheck } from './appCheck.js';

initializeAppCheck();

document.addEventListener('DOMContentLoaded', function () {
    const phoneNumberInput = document.getElementById('phone-number');
    const sendOtpButton = document.getElementById('send-otp-button');
    const otpField = document.getElementById('otp-field');
    const otpCodeInput = document.getElementById('otp-code');
    const verifyOtpButton = document.getElementById('verify-otp-button');
    const errorMessage = document.getElementById('error-message');

    // Initialize intl-tel-input
    const intlTelInputInstance = window.intlTelInput(phoneNumberInput, {
        initialCountry: "auto", // Set to 'auto' for automatic IP-based detection
        separateDialCode: true,
        geoIpLookup: function (success, failure) {
            fetch("https://ipapi.co/json/")
                .then(response => response.json())
                .then(data => {
                    success(data.country_code);
                })
                .catch(() => {
                    failure();
                });
        },
    });


    sendOtpButton.addEventListener('click', function () {
        const phoneNumber = intlTelInputInstance.getNumber();
        if (!phoneNumber) {
            errorMessage.textContent = "Please Enter Valid phone number";
            errorMessage.style.display = 'block';
            return;
        }

        auth.signInWithPhoneNumber(phoneNumber)
            .then((confirmationResult) => {
                window.confirmationResult = confirmationResult;
                otpField.style.display = 'block';
                errorMessage.style.display = 'none';
            })
            .catch((error) => {
                console.error("Error Sending OTP: ", error);
                errorMessage.textContent = "Error sending OTP. Please try again later";
                errorMessage.style.display = 'block';
            });
    });

    verifyOtpButton.addEventListener('click', function () {
        const otpCode = otpCodeInput.value;

        if (!otpCode) {
            errorMessage.textContent = "Please Enter OTP";
            errorMessage.style.display = 'block';
            return;
        }

        window.confirmationResult.confirm(otpCode)
            .then((result) => {
                // User signed in successfully.
                const user = result.user;
                console.log('User logged in:', user);
                errorMessage.textContent = "Login Sucessfull Redirecting..."
                errorMessage.style.display = 'block';
                setTimeout(() => {
                    window.location.href = "home.html";
                }, 3000);

            }).catch((error) => {
                console.error("Error verifying OTP:", error);
                errorMessage.textContent = "Invalid OTP. Please try again.";
                errorMessage.style.display = 'block';
            });
    });
});
