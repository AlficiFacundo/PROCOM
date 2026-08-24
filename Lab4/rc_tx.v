module moduleName #(
    parameter NB_COEFF = 8,
    parameter NB_OUT = NB_COEFF + $clog2{6} //8[3]
) (
    input wire clk,
    input wire i_rst_n,
    input wire en_tx,
    input wire prbs_bit,
    input wire prbs_en,
    input wire [2-1:0] phase_sel,
    output wire signed [] data_out
);
    //registro de desplazamiento de 6 baudios
    reg[6-1:0] shift_reg;
    always@(posedge clk or negedge i_rst_n) begin
        if(!i_rst_n)begin
            shift_reg <= 6'b0;
        end else if (en_tx && prbs_en)begin
            shift_reg <= {shift_reg[6-2:0],prbs_bit};
        end
    end
    //Fase 0 usa h0, h8, h12, h16, h20
    //Fase 1 usa h1, h9, h13, h17, h21
    //Fase 2 usa h2, h10, h14, h18, h22
    //Fase 3 usa h3, h11, h15, h19, h23
    localparam signed [NB_COEFF-1:0] phase_coeff [0:4-1] [0:6-1] = '{
        '{0,1,2,3,4,5,6}, //Fase 0 {coeff0, coeff1, coeff2, ..., coeff6}
        //hay que cambiar los valores obviamente, 0,1,2,3,4,5,6 son para ubicar los nombres nomas
        '{0,1,2,3,4,5,6}, //Fase 1
        '{0,1,2,3,4,5,6}, //Fase 2
        '{0,1,2,3,4,5,6}, //Fase 3
    }
    //Subfiltros en paralelo 
    wire signed [NB_OUT-1:0] sum [4-1:0];
    always@(*)begin
        sum[0] = 0;
        sum[1] = 0;
        sum[2] = 0;
        sum[3] = 0;

        sum[0] = sum[0] + (prbs_bit)? -phase_coeff[i][j] : phase_coef[i][j];
    end
endmodule