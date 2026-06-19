module shiftreg
#(
    parameter NB_LEDS = 4
)

(
    output[3:0]o_led ,

    input      i_valid,
    input      i_reset,
    input      clock
);

    reg [NB_LEDS-1:0] shiftreg;
    always@(posedge clock) begin
        if(i_reset) begin
        shiftreg <= {{{NB_LEDS-1{1'b0}}},1'b1};
        end

        else if (i_valid) begin
            shiftreg <= {shiftreg[0], shiftreg[NB_LEDS-1:1]};
        end
        else begin
            shiftreg <= shiftreg;
        end
    end
    assign o_led = shiftreg; 
endmodule