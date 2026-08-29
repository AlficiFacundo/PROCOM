module decimator #(
    parameter NB_COEFF = 9,
    parameter N_PHASES = 4
)(
    input  wire                          clk,
    input  wire                          i_rst_n,
    input  wire                          en_rx,
    input  wire [$clog2(N_PHASES)-1:0]   phase_cnt,
    input  wire [$clog2(N_PHASES)-1:0]   phase_sw,
    input  wire signed [NB_COEFF-1:0]    data_in_I,
    input  wire signed [NB_COEFF-1:0]    data_in_Q,
    output reg                           valid_dec,
    output reg                           dec_bit_I,
    output reg                           dec_bit_Q,
    output reg  signed [NB_COEFF-1:0]    dec_sample_I,
    output reg  signed [NB_COEFF-1:0]    dec_sample_Q
);
    wire match = en_rx && (phase_cnt == phase_sw);

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            valid_dec    <= 1'b0;
            dec_bit_I    <= 1'b0;
            dec_bit_Q    <= 1'b0;
            dec_sample_I <= {NB_COEFF{1'b0}};
            dec_sample_Q <= {NB_COEFF{1'b0}};
        end else begin
            valid_dec <= match;
            if (match) begin
                dec_sample_I <= data_in_I;
                dec_sample_Q <= data_in_Q;
                dec_bit_I    <= data_in_I[NB_COEFF-1]; // bit de signo = slicer
                dec_bit_Q    <= data_in_Q[NB_COEFF-1];
            end
        end
    end
endmodule