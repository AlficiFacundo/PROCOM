/*Este código enciende leds de una FPGA basándose en la entrada de switches.
(Ver diagrama en Unit01.pdf)*/
module topModule
(
    parameter NB_LEDS = 4,
    parameter NB_SW = 4,
    parameter NB_COUNTER = 32
)
(
    output[NB_LEDS-1:0] o_led , 
    output[NB_LEDS-1:0] o_led_b , 
    output[NB_LEDS-1:0] o_led_g ,

    /*Tambien se puede hacer de la siguiente manera la declaracion de puertos
    output[3:0] o_led , o_led_b , o_led_g
    cual es el problema de esto? los puertos tendran el mismo ancho y queda menos claro 
    la direccion de los mismos. Al tener varias capas, se complica*/

    input[3:0] i_sw , 
    input i_reset , 
    input clock 
);
//Variables internas
    wire connect_c2sf; //Conexión entre el contador y el shift register
    wire [NB_LEDS-1 :0] connect_leds; //Conexión entre el shift register y la salida de leds
//Instanciación de los módulos
    shiftreg
    #(
        .NB_LEDS(NB_LEDS)
    )
        u_shiftreg(
            .o_led(connect_leds),
            .i_valid(connect_c2sf),
            .i_reset(i_reset),
            .clock(clock)
        );

    count
    #(
        .NB_SW(NB_SW-1),
        .NB_COUNTER(NB_COUNTER)
    )
        u_count(
            .o_valid(connect_c2sf),
            .i_sw(i_sw[NB_SW-2:0]),
            .i_reset(i_reset),
            .clock(clock)
        );
    assign o_led = connect_leds; //Asignación de la salida de leds
    assign o_led_b = (i_sw[NB_SW-1]) ? connect_leds : 4'b0000; //Es una forma de if, testea lo que esta entre paréntesis
    //Si es verdadero, asigna lo que esta después del signo de interrogación, sino, lo que esta después de los dos puntos.
    assign o_led_g = (i_sw[NB_SW-1]) ? 4'b0000 : connect_leds;
endmodule