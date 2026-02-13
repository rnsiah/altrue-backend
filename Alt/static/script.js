// script.js

document.addEventListener("DOMContentLoaded", function() {
    const shirtItems = document.querySelectorAll(".shirt-item");
    const nonProfitItems = document.querySelectorAll(".non-profit-item");
    const submitBtn = document.getElementById("submitBtn");

    // Shirt selection logic
    shirtItems.forEach((item) => {
        item.addEventListener("click", function() {
            // Toggle selection status
            shirtItems.forEach((item) => item.classList.remove("selected"));
            this.classList.add("selected");
            console.log('cliked')
        });
    });

    // Non-profit selection logic
    nonProfitItems.forEach((item) => {
        item.addEventListener("click", function() {
            const isSelected = this.classList.contains('selected')
            nonProfitItems.forEach((item) => item.classList.remove("selected"));

            this.classList.add("selected");


            console.log('clicked')
        });
    });

    // Submit button click event
    submitBtn.addEventListener("click", function() {
        const selectedShirtElement = document.querySelector(".shirt-item.selected");
        const selectedShirtId = selectedShirtElement ?
            selectedShirtElement.dataset.shirtId :
            null;
        const selectedNonProfitIds = [
            ...document.querySelectorAll(".non-profit-item.selected"),
        ].map((item) => item.dataset.nonprofitId);

        console.log("Selected shirt ID:", selectedShirtId);
        console.log("Selected non-profit IDs:", selectedNonProfitIds);

        // Here, you can make an AJAX request to send the selected shirt ID and non-profit IDs to the server
    });
});