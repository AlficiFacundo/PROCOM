`timescale 1ns / 100ps  //1nS de escala y 100pS de paso
module tb_topModule;

    parameter NB_LEDS = 4;
    parameter NB_SW = 4;
    parameter NB_COUNTER = 16;
    //Entradas con reg y salidas con wire
    wire [NB_LEDS-1:0] o_led ; 
    wire [NB_LEDS-1:0] o_led_b ; 
    wire [NB_LEDS-1:0] o_led_g ;
    reg [3:0] i_sw ; 
    reg i_reset ; 
    reg clock ;
    topModule #(
        .NB_LEDS    (NB_LEDS),
        .NB_SW      (NB_SW),
        .NB_COUNTER (NB_COUNTER) 
    ) dut_top (
        .o_led   (o_led ), 
        .o_led_b (o_led_b ), 
        .o_led_g (o_led_g ),
        .i_sw    (i_sw ), 
        .i_reset (i_reset ), 
        .clock   (clock ) 
    );
    initial clock = 1'b0;
    always #5 clock = ~clock;
    initial begin
        i_sw = 4'b0000;
        i_reset = 1'b0; //El reset de la placa es activo por bajo.
        #100; //Espera de 100nS
        @(posedge clock); //Espero el flanco de reloj
        i_reset = 1'b1; //Desactivo el reset
        #100;
        @(posedge clock);
        i_sw = 4'b0001;
        #100;
        @(posedge clock);
        i_sw = 4'b0011;
        #100;
        @(posedge clock);
        i_sw = 4'b0101;
        #100;
        @(posedge clock);
        i_sw = 4'b0111;
        #100;
        @(posedge clock);
        i_sw = 4'b1111;
        #100;
        @(posedge clock);
        i_sw = 4'b1101;
        #100;
        @(posedge clock);
        i_sw = 4'b1011;
        #100;
        @(posedge clock);
        i_sw = 4'b1001;
        #100;
        $finish;
    end
endmodule
