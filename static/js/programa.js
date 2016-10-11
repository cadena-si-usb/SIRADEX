$(document).ready(function(){
  var maxLongNombre  = 256;    // Longitud máxima que tendrá el campo nombre.
  var maxLongDescrip = 2048;   // Longitud máxima que tendrá el campo descripción.

  // Obtengo la lista de errores generados por el formulario de agregar.
  var mensajeErrorAgregar = $("#modalAgregar").attr("data-hayErroresAgregar");
  mensajeErrorAgregar = mensajeErrorAgregar.replace(/<Storage |>/gi, "").replace(/'/g, '"')

  // Hay errores en el formulario agregar.
  if (mensajeErrorAgregar != '{}'){
      $("#agregarProgBtn").click();
      $(".error_wrapper").css('color','red');
  }

  // Muestra la cantidad de caracteres disponible en el textfield de nombre.
  textoRestante(maxLongNombre,  "#no_table_Nombre");

  // Muestra la cantidad de caracteres disponible en el textarea de descripción.
  textoRestante(maxLongDescrip, "#no_table_Descripcion");

  // $("#agregarBtn").click(function(){
  //     var contenidoNombre = $("#no_table_Nombre").html();
  //     var contenidoDescripcion = $("#no_table_Descripcion").html();
  //     var hayErrores = $("#modalAgregar").attr("data-hayErrores");
  //
  //     console.log("+ Contenido en nombre: " + contenidoNombre);
  //     console.log("+ Contenido en descripcion: " + contenidoDescripcion);
  //     console.log("hayErrores: " + hayErrores);
  //
  //
  //     return false;
  //});

});
