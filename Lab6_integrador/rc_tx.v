module rc_tx #(
    parameter NB_COEFF  = 9,   // S(9,7)
    parameter NBF_COEFF = 7,   // bits fraccionarios
    parameter N_BAUDS   = 6,   // simbolos o span
    parameter N_PHASES  = 4    // os
)(
    input  wire                          clk,
    input  wire                          i_rst_n,
    input  wire                          en_tx,
    input  wire                          prbs_bit,
    input  wire                          prbs_en,
    input  wire [$clog2(N_PHASES)-1:0]   phase_sel,
    output wire signed [NB_COEFF-1:0]    data_out
);
    reg [N_BAUDS-1:0] shift_reg;

    always @(posedge clk or negedge i_rst_n) begin
        if (!i_rst_n)
            shift_reg <= {N_BAUDS{1'b1}};
        else if (en_tx && prbs_en)
            shift_reg <= {shift_reg[N_BAUDS-2:0], prbs_bit};
    end

    // Banco de coeficientes S(9,7): phase_coeff[fase][i] = h[fase + i*N_PHASES]
    // rolloff=0.5, span=6, os=4, normalizado
    reg signed [NB_COEFF-1:0] phase_coeff [0:N_PHASES-1][0:N_BAUDS-1];
    initial begin
        phase_coeff[0][0]=9'h000; phase_coeff[0][1]=9'h000; phase_coeff[0][2]=9'h000;
        phase_coeff[0][3]=9'h057; phase_coeff[0][4]=9'h000; phase_coeff[0][5]=9'h000;

        phase_coeff[1][0]=9'h000; phase_coeff[1][1]=9'h1fb; phase_coeff[1][2]=9'h017;
        phase_coeff[1][3]=9'h04d; phase_coeff[1][4]=9'h1f5; phase_coeff[1][5]=9'h002;

        phase_coeff[2][0]=9'h001; phase_coeff[2][1]=9'h1f6; phase_coeff[2][2]=9'h034;
        phase_coeff[2][3]=9'h034; phase_coeff[2][4]=9'h1f6; phase_coeff[2][5]=9'h001;

        phase_coeff[3][0]=9'h002; phase_coeff[3][1]=9'h1f5; phase_coeff[3][2]=9'h04d;
        phase_coeff[3][3]=9'h017; phase_coeff[3][4]=9'h1fb; phase_coeff[3][5]=9'h000;
    end

    localparam signed [NB_COEFF-1:0] MAX_VAL = {1'b0, {(NB_COEFF-1){1'b1}}};
    localparam signed [NB_COEFF-1:0] MIN_VAL = {1'b1, {(NB_COEFF-1){1'b0}}};

    function automatic signed [NB_COEFF-1:0] sat_add;
        input signed [NB_COEFF-1:0] a;
        input signed [NB_COEFF-1:0] b;
        reg signed [NB_COEFF:0] ext; // 1 bit extra: suficiente para detectar overflow de a+b
        begin
            ext = $signed({a[NB_COEFF-1], a}) + $signed({b[NB_COEFF-1], b});
            if (ext > $signed({1'b0, MAX_VAL}))
                sat_add = MAX_VAL;
            else if (ext < $signed({1'b1, MIN_VAL}))
                sat_add = MIN_VAL;
            else
                sat_add = ext[NB_COEFF-1:0];
        end
    endfunction

    wire signed [NB_COEFF-1:0] term [0:N_BAUDS-1];
    wire signed [NB_COEFF-1:0] acc  [0:N_BAUDS];

    assign acc[0] = {NB_COEFF{1'b0}};

    genvar gi;
    generate
        for (gi = 0; gi < N_BAUDS; gi = gi + 1) begin : gen_acc
            assign term[gi] = shift_reg[gi] ? -phase_coeff[phase_sel][gi]
                                             :  phase_coeff[phase_sel][gi];
            assign acc[gi+1] = sat_add(acc[gi], term[gi]);
        end
    endgenerate

    assign data_out = acc[N_BAUDS];
endmodule