document.addEventListener("DOMContentLoaded", function() {
    var stripeApiKey = "pk_test_osCkw6g4MDSTjwXhs0RzOwL0";
    var stripe = Stripe(stripeApiKey);
    var elements = stripe.elements();
    var cardElement = elements.create("card");
    cardElement.mount("#card-element");

    var form = document.getElementById("payment-form");
    form.addEventListener("submit", function(event) {
        event.preventDefault();

        stripe.createToken(cardElement).then(function(result) {
            if (result.error) {
                // Display error.message in your UI
                document.getElementById("error-message").textContent =
                    result.error.message;
            } else {
                // Send the token to your server
                fetch("/process_payment/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken"),
                        },
                        body: JSON.stringify({
                            token: result.token.id,
                            email: form.email.value,
                            first_name: form.first_name.value,
                            last_name: form.last_name.value,
                            amount_donated: form.amount.value,
                            slug: form.slug.value,
                        }),
                    })
                    .then(function(response) {
                        return response.json();
                    })
                    .then(function(data) {
                        if (data.success) {
                            // Redirect to the thank you page
                            window.location.href = data.redirect_url;
                        } else {
                            // Display error in your UI
                            document.getElementById("error-message").textContent = data.error;
                        }
                    })
                    .catch(function(error) {
                        document.getElementById("error-message").textContent =
                            error.message;
                    });
            }
        });
    });

    // Function to get CSRF token from cookie
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            var cookies = document.cookie.split(";");
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});