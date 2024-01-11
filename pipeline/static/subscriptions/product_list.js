function getUserEmail() {
            var userEmail = document.getElementById('userEmail').value;
            console.log(userEmail)
            return userEmail
        }
        function deleteItem(element, productName) {
            var userEmail = getUserEmail()
            if (confirm("Are you sure you want to unsubscribe from receiving notifications for this product?")) {
                var xhr_request = new XMLHttpRequest();
                xhr_request.open("POST", "/delete_subscription", true);
                xhr_request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
                xhr_request.onreadystatechange = function() {
                    if (this.readyState == XMLHttpRequest.DONE && this.status == 200) {
                        element.parentNode.parentNode.remove();
                    }
                }
                xhr_request.send("product_name=" + encodeURIComponent(productName) + "&user_email=" + encodeURIComponent(userEmail));
            }
        }