module prbs9 #(
    parameter SEED = 9'h1AA
)(
    output wire prbs_bit,
    input wire clk,
    input wire i_rst_n,
    input wire en_tx, // i_sw[0]
    input wire prbs_en // proveniente del control
);
    reg [9-1:0] lfsr;
    wire fb = lfsr[0] ^ lfsr[4];
    always@(posedge clk or negedge i_rst_n)begin
        if (!i_rst_n) begin
            lfsr <= SEED;
        end else if (en_tx && prbs_en)begin
            lfsr <= {fb , lfsr[8:1]};
        end
    end
    //prbs_bit = 0 --> +1
    //prbs_bit = 1 --> -1
    assign prbs_bit = lfsr[0];
endmodule