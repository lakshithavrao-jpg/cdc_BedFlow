document.addEventListener("DOMContentLoaded", () => {

    // Close alert messages
    document.querySelectorAll(".close-alert").forEach(button => {

        button.addEventListener("click", () => {

            button.parentElement.remove();

        });

    });


    // Automatically hide alert messages after 6 seconds
    document.querySelectorAll(".alert").forEach(alert => {

        setTimeout(() => {

            alert.style.opacity = "0";

            setTimeout(() => {

                alert.remove();

            }, 400);

        }, 6000);

    });

});