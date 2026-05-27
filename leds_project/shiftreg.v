// Aquí va la lógica del módulo ShiftReg.
module shiftreg
(
    parameter NB_LEDS = 4
)

(
    output[3:0]o_led ,

    input      i_valid,
    input      i_reset,
    input      clock
);

//Variables internas
    reg [NB_LEDS-1:0] shiftreg; //Registro para el shift register
//Modelado del shift register
    always@(posedge clock) begin
        if(i_reset) begin
        shiftreg <= {{{NB_LEDS-1{1'b0}}},1'b1};//Si aparece el reset, el shift register se inicializa con un 1 en el LSB
        end

        else if (i_valid) begin
            /*Como hago que el shiftregister tenga un desplazamiento de 1? 4 Opciones:
            -Opción 1:
            +shiftreg <= shiftreg << 1; //El shift register hace un corrimiento lógico a la izquierda. También se puede hacer:
            +shiftreg[0] <= shiftreg[NB_LEDS-1]; //El LSB toma el valor del MSB
            -Opción 2:
            */
            shiftreg <= {shiftreg[NB_LEDS-2:0],shiftreg[NB_LEDS-1]};//Haciendo concatenación, la lógica es:
            /*
            -Los 3 bits menos significativos toman el valor de los 3 bits más significativos y el MSB toma el valor del LSB
            +shiftreg <= {shiftreg[0+:NB_LEDS-1],shiftreg[NB_LEDS-1]};
            +shiftreg <= {shiftreg[NB_LEDS-2:0],shiftreg[NB_LEDS-1]};
            
            -Opción 3:
            +for(ptr=0;ptr<NB_LEDS-1;ptr=ptr+1) begin : shiftAssign
                +shiftreg[ptr+1] <= shiftreg[ptr];
            +end
            +shiftreg[0] <= shiftreg[NB_LEDS-1];
            -Opción 4:
            +shiftreg[1] <= shiftreg[0];
            +shiftreg[2] <= shiftreg[1];
            +shiftreg[3] <= shiftreg[2];
            +shiftreg[0] <= shiftreg[3];
            -Esta opción es a fuerza bruta.
            */
        end
        else begin
            shiftreg <= shiftreg; //Si no se cumple ninguna condición, el shift register se mantiene.
        end
    end
    assign o_led = shiftreg; //Asignación de la salida
endmodule