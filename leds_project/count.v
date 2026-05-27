// Aquí va la lógica del módulo Count.
/* El nombre de cada módulo conviene que sea el mismo que el nombre de la entrada del mismo,
Para en casos donde se tienen varias capas, saber de que parte del código viene cada cosa.
Tenemos una frecuencia de referencia de 100MHz como referencia para las entradas del multiplexador*/
module count(
    parameter NB_SW = 3,
    parameter NB_COUNTER = 32 //Contador de 32 bits.
)
(
    //Salidas
    output o_valid,
    //Emtradas
    input [NB_SW-1:0] i_sw,
    input i_reset,
    input clock
);
//Local parameters (Solo para este módulo, con el fin de no hacer lineas innecesarias en la jerarquía del topModule)
// Definición de bits para el contador.
    localparam R0 =(2**(NB_COUNTER-10))-1;  //(2^22)-1
    localparam R1 =(2**(NB_COUNTER-8))-1;   //(2^24)-1
    localparam R2 =(2**(NB_COUNTER-6))-1;   //(2^26)-1
    localparam R3 =(2**(NB_COUNTER-2))-1;   //(2^30)-1
//Definición de variables internas.
    wire [NB_COUNTER-1:0] limit;
    reg  [NB_COUNTER-1:0] counter; //Registro para el contador
    reg                   valid;   //Registro para la salida de valid
//Modelado del contador
    assign limit=(i_sw[2:1]==2'b00)? R0:
                 (i_sw[2:1]==2'b01)? R1:
                 (i_sw[2:1]==2'b10)? R2: R3
    always@(posedge clock) 
    begin
        if(i_reset) //Al no poner nada, estoy planteando que i_reset debe ser 1 para pasar al if
            begin
                counter <= {NB_COUNTER{1'b0}}; //El contador se inicializa a 0 si aparece el reset
                valid <= 1'b0; //La salida valid se inicializa a 0 si aparece el reset
            end
        else if(i_sw[0]) 
            begin
                if(counter>=limit) //Para evitar pasar el límite en casos específicos (dado la diferencia de tamaño del contador y el límite)
                    begin
                        counter <= {NB_COUNTER{1'b0}};
                        valid <= 1'b1; //Cuando el contador llega al límite, valid se pone a 1
                    end
                else 
                    begin
                    counter <= counter + 'h1; /*El contador incrementa en 1
                    -No se debe poner un +1 directamente, sino que se debe hacer una concatenación 
                    -para que el tamaño del 1 sea igual al del contador, teniendo asi en cuenta los otros MSB
                    -También se puede hacer con un 'h1. Esta forma completa todos los bits con 0s a la izquierda
                    -sin importar el tamaño del contador.*/
                    valid <= 1'b0; //Mientras el contador no llega al límite, valid se mantiene en 0
                    end
            end
        else //Este else se usa debido a que usamos lógica no bloqueante, en caso contrario, las variables guardan el valor anterior.
            begin
                counter <= counter; //Si no se cumple ninguna condición, el contador se mantiene.
                valid <= valid; //Si no se cumple ninguna condición, valid se mantiene.
            end
    end
    assign o_valid = valid; //Asignación de la salida

endmodule