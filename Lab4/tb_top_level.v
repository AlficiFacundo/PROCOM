`timescale 1ns/1ps

module tb_top_level;
    localparam NB_COEFF = 9;
    localparam N_CYCLES = 801;

    reg  clk = 0;
    reg  i_rst_n;
    reg  [3:0] i_sw;

    reg                mem_i_rst [0:N_CYCLES-1];
    reg  [3:0]         mem_i_sw  [0:N_CYCLES-1];
    reg  [NB_COEFF-1:0] mem_exp_I [0:N_CYCLES-1];
    reg  [NB_COEFF-1:0] mem_exp_Q [0:N_CYCLES-1];

    wire signed [NB_COEFF-1:0] o_sample_I, o_sample_Q;
    wire [3:0] o_led;
    localparam CNT_WIDTH = 24;
    wire [CNT_WIDTH-1:0] o_err_I, o_tot_I, o_err_Q, o_tot_Q;
    reg  [1:0] fase_prev;

    top_level dut (
        .clk(clk),
        .i_rst_n(i_rst_n),
        .i_sw(i_sw),
        .o_led(o_led),
        .o_sample_I(o_sample_I),
        .o_sample_Q(o_sample_Q),
        .o_err_I(o_err_I),
        .o_tot_I(o_tot_I),
        .o_err_Q(o_err_Q),
        .o_tot_Q(o_tot_Q)
    );

    always #5 clk = ~clk;

    integer idx;
    integer errores;

    initial begin
        $readmemb("stim_i_rst.mem",       mem_i_rst);
        $readmemb("stim_i_sw.mem",        mem_i_sw);
        $readmemh("expected_sample_I.mem", mem_exp_I);
        $readmemh("expected_sample_Q.mem", mem_exp_Q);

        errores = 0;
        i_rst_n = 1'b1;
        i_sw    = 4'b0;
        fase_prev = i_sw[3:2];

        for (idx = 0; idx < N_CYCLES; idx = idx + 1) begin
            i_rst_n = ~mem_i_rst[idx];
            i_sw    = mem_i_sw[idx];
            @(posedge clk);
            #1;
            if (o_sample_I !== mem_exp_I[idx]) begin
                errores = errores + 1;
            end
            if (o_sample_Q !== mem_exp_Q[idx]) begin
                errores = errores + 1;
            end
            if (idx > 0 && i_sw[3:2] !== fase_prev) begin
                $display("BER fase %0d: I = %0d/%0d  Q = %0d/%0d", fase_prev, o_err_I, o_tot_I, o_err_Q, o_tot_Q);
                fase_prev = i_sw[3:2];
            end
        end
        $display("BER fase %0d: I = %0d/%0d  Q = %0d/%0d", fase_prev, o_err_I, o_tot_I, o_err_Q, o_tot_Q);
        $display("Vector Matching finalizado: %0d mismatches de %0d ciclos", errores, N_CYCLES);
        $finish;
    end
endmodule