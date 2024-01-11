document.addEventListener('DOMContentLoaded', function() {
        var form = document.querySelector('form');
        var submitButton = form.querySelector('button[type="submit"]');
        var firstNameInput = form.querySelector('input[name="firstName"]');
        var lastNameInput = form.querySelector('input[name="lastName"]');
        var emailInput = form.querySelector('input[type="email"]');
        var urlInput = form.querySelector('input[type="url"]');
        var firstNameErrorMessage = document.getElementById('first-name-error-message');
        var lastNameErrorMessage = document.getElementById('last-name-error-message');
        var emailErrorMessage = document.getElementById('email-error-message');
        var urlErrorMessage = document.getElementById('error-message');
        var validWebsites = ["www.asos.com"];

        function getDomain(url) {
            var hostname;
            if (url.indexOf("://") > -1) {
                hostname = url.split('/')[2];
            } else {
                hostname = url.split('/')[0];
            }
            hostname = hostname.split(':')[0];
            hostname = hostname.split('?')[0];
            return hostname;
        }

        function checkInputValidity() {
            var isFirstNameValid = firstNameInput.value.trim() !== '';
            var isLastNameValid = lastNameInput.value.trim() !== '';
            var isEmailValid = emailInput.validity.valid;
            var urlDomain = getDomain(urlInput.value);
            var isUrlValid = validWebsites.includes(urlDomain) && urlInput.value.trim() !== '';

            firstNameErrorMessage.style.display = isFirstNameValid ? 'none' : 'block';
            lastNameErrorMessage.style.display = isLastNameValid ? 'none' : 'block';
            emailErrorMessage.style.display = isEmailValid ? 'none' : 'block';
            urlErrorMessage.style.display = isUrlValid ? 'none' : 'block';

            return isFirstNameValid && isLastNameValid && isEmailValid && isUrlValid;
        }

        form.addEventListener('submit', function(event) {
            var isFormValid = checkInputValidity();
            if (!isFormValid) {
                event.preventDefault();
            }
        });

        Array.from(form.elements).forEach(function(element) {
            element.addEventListener('input', function() {
                firstNameErrorMessage.style.display = 'none';
                lastNameErrorMessage.style.display = 'none';
                emailErrorMessage.style.display = 'none';
                urlErrorMessage.style.display = 'none';
            });
        });
    });