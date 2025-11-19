// ui_utils.js

export const UI_UTILS = {

    mostrarError(idElemento, mensaje) {
        const elemento = document.getElementById(idElemento);
        if (elemento) {
            elemento.style.display = "block";
            elemento.innerText = mensaje;
        }
    },

    ocultarError(idElemento) {
        const elemento = document.getElementById(idElemento);
        if (elemento) {
            elemento.style.display = "none";
        }
    },

    mostrarCarga(idElemento) {
        const elemento = document.getElementById(idElemento);
        if (elemento) elemento.style.display = "block";
    },

    ocultarCarga(idElemento) {
        const elemento = document.getElementById(idElemento);
        if (elemento) elemento.style.display = "none";
    }

};
