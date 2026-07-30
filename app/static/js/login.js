const form = document.getElementById("login-form");
const button = form.querySelector("button[type='submit']");

form.addEventListener("submit", async (e) => {

  e.preventDefault();

  button.disabled = true;
  button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Signing in...`;

  try {

    const response = await fetch(form.action || window.location.pathname, {
      method: "POST",
      body: new FormData(form)
    });

    const data = await response.json();

    if (data.success) {
      window.location.href = data.redirect;
      return;
    }

    showNotification(data.message, data.category, data.title);

    const username = form.username;
    const password = form.password;

    username.value = "";
    password.value = "";

    username.classList.add("is-invalid");
    password.classList.add("is-invalid");

    username.focus();
    form.username.addEventListener("input", () => { form.username.classList.remove("is-invalid"); });
    form.password.addEventListener("input", () => { form.password.classList.remove("is-invalid"); });


  } catch (err) {

    console.error(err);

    showNotification(`Unable to communicate with the server.\n\n ${err}`, "error", "Connection Error");

  } finally {

    button.disabled = false;
    button.innerHTML = "Login";

  }

});
