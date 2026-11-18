document.addEventListener("DOMContentLoaded", function () {

    // Registration role selection

    const roleSelect = document.getElementById("roleSelect");

    const patientFields = document.getElementById("patientFields");


    function updateFields() {

        if (roleSelect && patientFields) {

            if (roleSelect.value === "patient") {

                patientFields.style.display = "grid";

            } else {

                patientFields.style.display = "none";

            }

        }

    }


    if (roleSelect) {

        roleSelect.addEventListener(
            "change",
            updateFields
        );

        updateFields();

    }


    // Prevent repeated form submissions

    document.querySelectorAll("form").forEach(function (form) {

        form.addEventListener("submit", function () {

            const button = form.querySelector(
                'button[type="submit"]'
            );

            if (button && !button.dataset.noDisable) {

                button.disabled = true;

                button.dataset.original = button.textContent;

                button.textContent = "Please wait...";

                setTimeout(function () {

                    button.disabled = false;

                    button.textContent = button.dataset.original;

                }, 5000);

            }

        });

    });

});